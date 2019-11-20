#!/usr/bin/env python3.5
import genericIO
import SepVector
import Hypercube
import numpy as np
import time
import sys
import os

# Modeling operators
import Acoustic_iso_float
import interpBSplineModule
import dataTaperModule
import spatialDerivModule
import dsoGpuModule
import dsoInvGpuModule

# Solver library
import pyOperator as pyOp
import pyLCGsolver as LCG
import pySymLCGsolver as SymLCGsolver
import pyProblem as Prblm
import pyStopperBase as Stopper
import inversionUtils
from sys_util import logger

#Dask-related modules
from dask_util import DaskClient
import pyDaskOperator as DaskOp

# Template for linearized waveform inversion workflow
if __name__ == '__main__':

	# IO object
	parObject=genericIO.io(params=sys.argv)

	pyinfo=parObject.getInt("pyinfo",1)
	spline=parObject.getInt("spline",0)
	dataTaper=parObject.getInt("dataTaper",0)
	regType=parObject.getString("reg","None")
	reg=0
	if (regType != "None"): reg=1
	epsilonEval=parObject.getInt("epsilonEval",0)

	# Initialize parameters for inversion
	stop,logFile,saveObj,saveRes,saveGrad,saveModel,prefix,bufferSize,iterSampling,restartFolder,flushMemory,info=inversionUtils.inversionInit(sys.argv)
	# Logger
	inv_log = logger(logFile)

	if(pyinfo): print("-------------------------------------------------------------------")
	if(pyinfo): print("-------------------- Extended linearized inversion ----------------")
	if(pyinfo): print("-------------------------------------------------------------------\n")
	inv_log.addToLog("-------------------- Extended linearized inversion ----------------")

	############################# Initialization ###############################
	# Spline
	if (spline==1):
		modelCoarseInit,modelFineInit,zOrder,xOrder,yOrder,zSplineMesh,xSplineMesh,ySplineMesh,zDataAxis,xDataAxis,yDataAxis,nzParam,nxParam,nyParam,scaling,zTolerance,xTolerance,yTolerance,zFat,xFat,yFat=interpBSplineModule.bSpline3dInit(sys.argv)

	# Data taper
	if (dataTaper==1):
		t0,velMute,expTime,taperWidthTime,moveout,reverseTime,maxOffset,expOffset,taperWidthOffset,reverseOffset,time,offset,shotRecTaper,taperShotWidth,taperRecWidth,expShot,expRec,edgeValShot,edgeValRec,taperEndTraceWidth=dataTaperModule.dataTaperInit(sys.argv)

	# Born extended
	modelFineInit,data,vel,parObject,sourcesVector,sourcesSignalsVector,receiversVector=Acoustic_iso_float.BornExtOpInitFloat(sys.argv)

	############################# Read files ###################################
	# Read initial model
	modelInitFile=parObject.getString("modelInit","None")
	if (spline==1):
		if (modelInitFile=="None"):
			modelInit=modelCoarseInit.clone()
			modelInit.scale(0.0)
		else:
			modelInit=genericIO.defaultIO.getVector(modelInitFile,ndims=3)

	else:
		if (modelInitFile=="None"):
			modelInit=modelFineInit.clone()
			modelInit.scale(0.0)
		else:
			modelInit=genericIO.defaultIO.getVector(modelInitFile,ndims=3)

	# Data
	dataFile=parObject.getString("data")
	data=genericIO.defaultIO.getVector(dataFile,ndims=3)

	############################# Instanciation ################################
	# Born
	BornExtOp=Acoustic_iso_float.BornExtShotsGpu(modelFineInit,data,vel,parObject.param,sourcesVector,sourcesSignalsVector,receiversVector)
	invOp=BornExtOp

	# Spline
	if (spline==1):
		if(pyinfo): print("--- Using spline interpolation ---")
		inv_log.addToLog("--- Using spline interpolation ---")
		splineOp=interpBSplineModule.bSpline3d(modelCoarseInit,modelFineInit,zOrder,xOrder,yOrder,zSplineMesh,xSplineMesh,ySplineMesh,zDataAxis,xDataAxis,yDataAxis,nzParam,nxParam,nyParam,scaling,zTolerance,xTolerance,yTolerance,zFat,xFat,yFat)

	# Data taper
	if (dataTaper==1):
		if(pyinfo): print("--- Using data tapering ---")
		inv_log.addToLog("--- Using data tapering ---")
		dataTaperOp=dataTaperModule.datTaper(data,data,t0,velMute,expTime,taperWidthTime,moveout,reverseTime,maxOffset,expOffset,taperWidthOffset,reverseOffset,data.getHyper(),time,offset,shotRecTaper,taperShotWidth,taperRecWidth,expShot,expRec,edgeValShot,edgeValRec,taperEndTraceWidth)
		dataTapered=data.clone()
		dataTaperOp.forward(False,data,dataTapered) # Apply tapering to the data
		data=dataTapered

	if (regType != "dsoPrec"):
		# Concatenate operators
		if (spline==1 and dataTaper==0):
			invOp=pyOp.ChainOperator(splineOp,BornExtOp)
		if (spline==0 and dataTaper==1):
			invOp=pyOp.ChainOperator(BornExtOp,dataTaperOp)
		if (spline==1 and dataTaper==1):
			invOpTemp=pyOp.ChainOperator(splineOp,BornExtOp)
			invOp=pyOp.ChainOperator(invOpTemp,dataTaperOp)

	# Preconditioning with DSO inverse
	if (reg==1 and regType=="dsoPrec"):

		# Instanciate Dso inverse operator
		# If we also use spline, the sequence is Born(Spline(DsoInverse(p)))
		nz,nx,nExt,fat,dsoZeroShift=dsoInvGpuModule.dsoInvGpuInit(sys.argv)
		nz=modelInit.getHyper().axes[0].n
		nx=modelInit.getHyper().axes[1].n
		nExt=modelInit.getHyper().axes[2].n
		fat=0
		dsoInvOp=dsoInvGpuModule.dsoInvGpu(modelInit,modelInit,nz,nx,nExt,fat,dsoZeroShift)

		# Concatenate operators
		if (spline==1 and dataTaper==0):
			splineTempOp=pyOp.ChainOperator(dsoInvOp,splineOp)
			invOp=pyOp.ChainOperator(splineTempOp,BornExtOp)
		if (spline==0 and dataTaper==1):
			invOpTemp=pyOp.ChainOperator(dsoInvOp,BornExtOp)
			invOp=pyOp.ChainOperator(invOpTemp,dataTaperOp)
		if (spline==1 and dataTaper==1):
			splineTempOp=pyOp.ChainOperator(dsoInvOp,splineOp)
			invOpTemp=pyOp.ChainOperator(splineTempOp,BornExtOp)
			invOp=pyOp.ChainOperator(invOpTemp,dataTaperOp)

	############################# Regularization ###############################
	# Regularization
	if (reg==1):
		# Get epsilon value from user
		epsilon=parObject.getFloat("epsilon",-1.0)
		inv_log.addToLog("--- Epsilon value: %s ---"%(epsilon))

		# Identity regularization
		if (regType=="id"):
			if(pyinfo): print("--- Identity regularization ---")
			inv_log.addToLog("--- Identity regularization ---")
			invProb=Prblm.ProblemL2LinearReg(modelInit,data,invOp,epsilon)

		# Dso
		elif (regType=="dso"):
			if(pyinfo): print("--- DSO regularization ---")
			inv_log.addToLog("--- DSO regularization ---")

			if (spline==1):
				# If using spline, the model dimensions change, you apply the DSO on the coarse grid
				nz,nx,nExt,fat,dsoZeroShift=dsoGpuModule.dsoGpuInit(sys.argv)
				nz=modelInit.getHyper().axes[0].n
				nx=modelInit.getHyper().axes[1].n
				nExt=modelInit.getHyper().axes[2].n
				fat=0
				dsoOp=dsoGpuModule.dsoGpu(modelInit,modelInit,nz,nx,nExt,fat,dsoZeroShift)
				invProb=Prblm.ProblemL2LinearReg(modelInit,data,invOp,epsilon,reg_op=dsoOp)
			else:
				nz,nx,nExt,fat,dsoZeroShift=dsoGpuModule.dsoGpuInit(sys.argv)
				dsoOp=dsoGpuModule.dsoGpu(modelInit,modelInit,nz,nx,nExt,fat,dsoZeroShift)
				invProb=Prblm.ProblemL2LinearReg(modelInit,data,invOp,epsilon,reg_op=dsoOp)

		elif (regType=="dsoPrec"):
			if(pyinfo): print("--- DSO regularization with preconditioning ---")
			inv_log.addToLog("--- DSO regularization with preconditioning ---")
			invProb=Prblm.ProblemL2LinearReg(modelInit,data,invOp,epsilon)

		else:
			if(pyinfo): print("--- Regularization that you have required is not supported by our code ---")
			quit()

		# Evaluate Epsilon
		if (epsilonEval==1):
			if(pyinfo): print("--- Epsilon evaluation ---")
			inv_log.addToLog("--- Epsilon evaluation ---")
			epsilonOut=invProb.estimate_epsilon()
			if(pyinfo): print("--- Epsilon value: ",epsilonOut," ---")
			inv_log.addToLog("--- Epsilon value: %s ---"%(epsilonOut))
			quit()

	# No regularization
	else:
		invProb=Prblm.ProblemL2Linear(modelInit,data,invOp)

	############################## Solver ######################################
	# Solver
	LCGsolver=LCG.LCGsolver(stop,logger=inv_log)
	LCGsolver.setDefaults(save_obj=saveObj,save_res=saveRes,save_grad=saveGrad,save_model=saveModel,prefix=prefix,iter_buffer_size=bufferSize,iter_sampling=iterSampling,flush_memory=flushMemory)

	# Run solver
	LCGsolver.run(invProb,verbose=True)

	if(pyinfo): print("-------------------------------------------------------------------")
	if(pyinfo): print("--------------------------- All done ------------------------------")
	if(pyinfo): print("-------------------------------------------------------------------\n")
