#!/usr/bin/env python3.5
import genericIO
import SepVector
import Hypercube
import numpy as np
import dsoInvGpuModule
import matplotlib.pyplot as plt
import sys
import time

if __name__ == '__main__':

	# Bullshit stuff
	io=genericIO.pyGenericIO.ioModes(sys.argv)
	ioDef=io.getDefaultIO()
	parObject=ioDef.getParamObj()
	adj=parObject.getInt("adj",0)

	nz,nx,nExt,fat,zeroShift=dsoInvGpuModule.dsoInvGpuInit(sys.argv)

	# Forward
	if (adj==0):

		# Read model (on coarse grid)
		modelFile=parObject.getString("model")
		model=genericIO.defaultIO.getVector(modelFile)

		# Create data
		data=model.clone()

		# Create DSO object and run forward
		dsoInvOp=dsoInvGpuModule.dsoInvGpu(model,data,nz,nx,nExt,fat,zeroShift)
		dsoInvOp.forward(False,model,data)

		# Write data
		dataFile=parObject.getString("data")
		genericIO.defaultIO.writeVector(dataFile,data)


	# Adjoint
	else:

		# Read data
		dataFile=parObject.getString("data")
		data=genericIO.defaultIO.getVector(dataFile)

		# Create model
		model=data.clone()

		# Create DSO object and run forward
		dsoInvOp=dsoInvGpuModule.dsoInvGpu(model,data,nz,nx,nExt,fat,zeroShift)
		dsoInvOp.adjoint(False,model,data)

		# Write model
		modelFile=parObject.getString("model")
		genericIO.defaultIO.writeVector(modelFile,model)
