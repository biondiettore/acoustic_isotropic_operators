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
import interpBSpline2dModule
import dataTaperModule
import spatialDerivModule

# Solver library
import pyOperator as pyOp
import pyNLCGsolver as NLCG
import pyProblem as Prblm
import pyStopperBase as Stopper
from sys_util import logger

# Template for FWI workflow
if __name__ == '__main__':

	# Bullshit stuff
	io=genericIO.pyGenericIO.ioModes(sys.argv)
	ioDef=io.getDefaultIO()
	parObject=ioDef.getParamObj()
	spline=parObject.getInt("spline",0)
	dataTaper=parObject.getInt("dataTaper",0)
	regType=parObject.getString("reg","None")
	reg=0
	if (regType != "None"): reg=1
	epsilonEval=parObject.getInt("epsilonEval",0)

	print("-------------------------------------------------------------------")
	print("------------------------------ FWIME ------------------------------")
	print("-------------------------------------------------------------------\n")

	############################# Initialization ###############################
	# Nonlinear forward operator #1:
    # model=velocity, data=seismic data
	model,data,wavelet,parObject,sourcesVector,receiversVector=Acoustic_iso_float.nonlinearFwiOpInitFloat(sys.argv)

    # Born non-extended (model=velocity perturbation, datat=Born data, set background velocity)
	_,_,_,_,_,sourcesSignalsVector,_=Acoustic_iso_float.BornOpInitFloat(sys.argv)

	# Nonlinear forward operator #2:
	# Born extended (model=velocity, data=Born data, set reflectivity)
    Acoustic_iso_float.BornExtOpInitFloat(sys.argv)

    # Tomo (model=velocity perturbation, data=tomo data, set background velocity)
    Acoustic_iso_float.tomoExtOpInitFloat(sys.argv)

	############################# Read files ###################################
	# Seismic source
	waveletFile=parObject.getString("sources")
	wavelet=genericIO.defaultIO.getVector(waveletFile,ndims=3)

	# Data
	dataFile=parObject.getString("data")
	data=genericIO.defaultIO.getVector(dataFile,ndims=3)

	############################# Instanciation ################################
	# Nonlinear
	nonlinearFwiOp=Acoustic_iso_float.nonlinearFwiPropShotsGpu(modelFineInit,data,wavelet,parObject,sourcesVector,receiversVector)

	# Born
	BornOp=Acoustic_iso_float.BornShotsGpu(modelFineInit,data,modelFineInit,parObject,sourcesVector,sourcesSignalsVector,receiversVector)

	# Conventional FWI
	fwiOp=pyOp.NonLinearOperator(nonlinearFwiOp,BornOp,BornOp.setVel)
	fwiInvOp=fwiOp
	modelInit=modelFineInit

	# Spline
	if (spline==1):
		print("--- Using spline interpolation ---")
		modelInit=modelCoarseInit
		splineOp=interpBSpline2dModule.bSpline2d(modelCoarseInit,modelFineInit,zOrder,xOrder,zSplineMesh,xSplineMesh,zDataAxis,xDataAxis,nzParam,nxParam,scaling,zTolerance,xTolerance,fat)
		splineNlOp=pyOp.NonLinearOperator(splineOp,splineOp) # Create spline nonlinear operator

	# Data taper
	if (dataTaper==1):
		print("--- Using data tapering ---")
		dataTaperOp=dataTaperModule.datTaper(data,data,t0,velMute,expTime,taperWidthTime,moveout,reverseTime,maxOffset,expOffset,taperWidthOffset,reverseOffset,data.getHyper(),time,offset)
		dataTapered=data.clone()
		dataTaperOp.forward(False,data,dataTapered) # Apply tapering to the data
		data=dataTapered
		dataTaperNlOp=pyOp.NonLinearOperator(dataTaperOp,dataTaperOp) # Create dataTaper nonlinear operator

	# Concatenate operators
	if (spline==1 and dataTaper==0):
		fwiInvOp=pyOp.CombNonlinearOp(splineNlOp,fwiOp)
	if (spline==0 and dataTaper==1):
		fwiInvOp=pyOp.CombNonlinearOp(fwiOp,dataTaperNlOp)
	if (spline==1 and dataTaper==1):
		fwiInvOpTemp=pyOp.CombNonlinearOp(splineNlOp,fwiOp) # Combine spline and FWI
		fwiInvOp=pyOp.CombNonlinearOp(fwiInvOpTemp,dataTaperNlOp) # Combine everything

	############################# Gradient mask ################################
	maskGradientFile=parObject.getString("maskGradient","NoMaskGradientFile")
	if (maskGradientFile=="NoMaskGradientFile"):
		maskGradient=None
	else:
		maskGradient=genericIO.defaultIO.getVector(maskGradientFile,ndims=2)

	############################### Bounds #####################################
	minBoundVector,maxBoundVector=Acoustic_iso_float.createBoundVectors(parObject,modelInit)

	############################# Regularization ###############################
	# Regularization
	if (reg==1):
		# Get epsilon value from user
		epsilon=parObject.getFloat("epsilon",-1.0)

		# Identity regularization
		if (regType=="id"):
			print("--- Identity regularization ---")
			fwiProb=Prblm.ProblemL2NonLinearReg(modelInit,data,fwiInvOp,epsilon,grad_mask=maskGradient,minBound=minBoundVector,maxBound=maxBoundVector)

		# Spatial gradient in z-direction
		if (regType=="zGrad"):
			print("--- Vertical gradient regularization ---")
			fat=spatialDerivModule.zGradInit(sys.argv)
			gradOp=spatialDerivModule.zGradPython(modelInit,modelInit,fat)
			gradNlOp=pyOp.NonLinearOperator(gradOp,gradOp)
			fwiProb=Prblm.ProblemL2NonLinearReg(modelInit,data,fwiInvOp,epsilon,grad_mask=maskGradient,reg_op=gradNlOp,minBound=minBoundVector,maxBound=maxBoundVector)

		# Spatial gradient in x-direction
		if (regType=="xGrad"):
			print("--- Horizontal gradient regularization ---")
			fat=spatialDerivModule.xGradInit(sys.argv)
			gradOp=spatialDerivModule.xGradPython(modelInit,modelInit,fat)
			gradNlOp=pyOp.NonLinearOperator(gradOp,gradOp)
			fwiProb=Prblm.ProblemL2NonLinearReg(modelInit,data,fwiInvOp,epsilon,grad_mask=maskGradient,reg_op=gradNlOp,minBound=minBoundVector,maxBound=maxBoundVector)

		# Sum of spatial gradients in z and x-directions
		if (regType=="zxGrad"):
			print("--- Gradient regularization in both directions ---")
			fat=spatialDerivModule.zxGradInit(sys.argv)
			gradOp=spatialDerivModule.zxGradPython(modelInit,modelInit,fat)
			gradNlOp=pyOp.NonLinearOperator(gradOp,gradOp)
			fwiProb=Prblm.ProblemL2NonLinearReg(modelInit,data,fwiInvOp,epsilon,grad_mask=maskGradient,reg_op=gradNlOp,minBound=minBoundVector,maxBound=maxBoundVector)

		# Evaluate Epsilon
		if (epsilonEval==1):
			print("--- Epsilon evaluation ---")
			epsilonOut=fwiProb.estimate_epsilon()
			print("--- Epsilon value: ",epsilonOut," ---")
			quit()

	# No regularization
	else:
		fwiProb=Prblm.ProblemL2NonLinear(modelInit,data,fwiInvOp,grad_mask=maskGradient,minBound=minBoundVector,maxBound=maxBoundVector)

	############################# Solver #######################################
	# Stopper
	stop=Stopper.BasicStopper(niter=parObject.getInt("nIter"))

	# Folder
	folder=parObject.getString("folder")
	if (os.path.isdir(folder)==False): os.mkdir(folder)
	prefix=parObject.getString("prefix","None")
	if (prefix=="None"): prefix=folder
	invPrefix=folder+"/"+prefix
	logFile=invPrefix+"_logFile"

	# Solver recording parameters
	iterSampling=parObject.getInt("iterSampling",1)
	bufferSize=parObject.getInt("bufferSize",-1)
	if (bufferSize<0): bufferSize=None

	# Solver
	NLCGsolver=NLCG.NLCGsolver(stop,logger=logger(logFile))

	# Manual step length
	initStep=parObject.getInt("initStep",-1)
	if (initStep>0):
		NLCGsolver.stepper.alpha=initStep

	# Solver
	NLCGsolver.setDefaults(save_obj=True,save_res=True,save_grad=True,save_model=True,prefix=invPrefix,iter_buffer_size=bufferSize,iter_sampling=iterSampling)

	# Run solver
	NLCGsolver.run(fwiProb,verbose=True)

	print("-------------------------------------------------------------------")
	print("--------------------------- All done ------------------------------")
	print("-------------------------------------------------------------------\n")