#!/usr/bin/env python3.5
import genericIO
import SepVector
import Hypercube
import numpy as np
import interpBSplineModule
import matplotlib.pyplot as plt
import sys
import time

if __name__ == '__main__':

	# Bullshit stuff
	io=genericIO.pyGenericIO.ioModes(sys.argv)
	ioDef=io.getDefaultIO()
	parObject=ioDef.getParamObj()
	nDim=parObject.getInt("nDim")
	adj=parObject.getInt("adj",0)
	param=parObject.getInt("meshOut",0) # Set to 1 if you want to write the mesh vectors and other interpolation parameters

	################################### 2d spline ##############################
	if (nDim==2):

		# Initialize 2d spline
		modelTemp,dataTemp,zOrder,xOrder,zSplineMesh,xSplineMesh,zDataAxis,xDataAxis,nzParam,nxParam,scaling,zTolerance,xTolerance,fat=interpBSplineModule.bSpline2dInit(sys.argv)

		# Construc 2d spline operator
		splineOp=interpBSplineModule.bSpline2d(modelTemp,dataTemp,zOrder,xOrder,zSplineMesh,xSplineMesh,zDataAxis,xDataAxis,nzParam,nxParam,scaling,zTolerance,xTolerance,fat)

		if (adj==0):

			print("-------------------------------------------------------------------")
			print("-------------- Running Spline interpolation forward ---------------")
			print("--------------------- 2D B-Splines functions ----------------------")
			print("-------------------------------------------------------------------\n")

			# Read model (on coarse grid)
			modelFile=parObject.getString("model")
			model=genericIO.defaultIO.getVector(modelFile,ndims=3)
			modelNd=model.getNdArray()

			# Get number of iterations
			nIter=model.getHyper().axes[2].n
			iterAxis=Hypercube.axis(n=nIter)

			# Temporary model
			modelTempNd=modelTemp.getNdArray()
			modelTemp.scale(0.0)

			# Create data vector
			zAxisData=dataTemp.getHyper().axes[0]
			xAxisData=dataTemp.getHyper().axes[1]
			dataHyper=Hypercube.hypercube(axes=[zAxisData,xAxisData,iterAxis])
			data=SepVector.getSepVector(dataHyper)
			dataNd=data.getNdArray()
			dataTempNd=dataTemp.getNdArray()

			# Apply spline interpolation fwd
			for iIter in range(nIter):

				print("iIter=",iIter)

				# Copy model to model temp for iIter
				modelTempNd[:]=modelNd[iIter,:]

				# Apply forward
				splineOp.forward(False,modelTemp,dataTemp)

				# Copy data temp to data
				dataNd[iIter,:]=dataTempNd[:]

			# Write data
			dataFile=parObject.getString("data")
			genericIO.defaultIO.writeVector(dataFile,data)

		else:

			print("-------------------------------------------------------------------")
			print("-------------- Running Spline interpolation adjoint ---------------")
			print("--------------------- 2D B-Splines functions ----------------------")
			print("-------------------------------------------------------------------\n")

			# Read data (fine grid)
			dataFile=parObject.getString("data")
			data=genericIO.defaultIO.getVector(dataFile,ndims=3)
			dataNd=data.getNdArray()

			# Get number of iterations
			nIter=data.getHyper().axes[2].n
			iterAxis=Hypercube.axis(n=nIter)

			# Temporary data
			dataTempNd=dataTemp.getNdArray()
			dataTemp.scale(0.0)

			# Create model vector
			zAxisModel=modelTemp.getHyper().axes[0]
			xAxisModel=modelTemp.getHyper().axes[1]
			model=SepVector.getSepVector(Hypercube.hypercube(axes=[zAxisModel,xAxisModel,iterAxis]))
			modelNd=model.getNdArray()
			modelTempNd=modelTemp.getNdArray()

			# Apply spline interpolation fwd
			for iIter in range(nIter):

				# Copy model to data temp for iIter
				dataTempNd[:]=dataNd[iIter,:]

				# Apply adjoint
				splineOp.adjoint(False,modelTemp,dataTemp)

				# Copy data temp to data
				modelNd[iIter,:]=modelTempNd[:]

			# Write model
			modelFile=parObject.getString("model")
			genericIO.defaultIO.writeVector(modelFile,model)

	if (param==1):

		# Write zMeshVector
		zMeshModel=splineOp.getZMeshModel()
		zMeshModelFile=parObject.getString("zMeshModel","junk")
		genericIO.defaultIO.writeVector(zMeshModelFile,zMeshModel)

		# Write zMeshDataVector (fine grid)
		zMeshData=splineOp.getZMeshData()
		zMeshDataFile=parObject.getString("zMeshData","junk")
		genericIO.defaultIO.writeVector(zMeshDataFile,zMeshData)

		# Write control points positions
		zMeshModel1d=splineOp.getZMeshModel1d()
		zMeshModel1dFile=parObject.getString("zMeshModel1d","junk")
		genericIO.defaultIO.writeVector(zMeshModel1dFile,zMeshModel1d)

		# Write zMeshVector
		xMeshModel=splineOp.getXMeshModel()
		xMeshModelFile=parObject.getString("xMeshModel","junk")
		genericIO.defaultIO.writeVector(xMeshModelFile,xMeshModel)

		# Write zMeshDataVector (fine grid)
		xMeshData=splineOp.getXMeshData()
		xMeshDataFile=parObject.getString("xMeshData","junk")
		genericIO.defaultIO.writeVector(xMeshDataFile,xMeshData)

		# Write control points positions
		xMeshModel1d=splineOp.getXMeshModel1d()
		xMeshModel1dFile=parObject.getString("xMeshModel1d","junk")
		genericIO.defaultIO.writeVector(xMeshModel1dFile,xMeshModel1d)
