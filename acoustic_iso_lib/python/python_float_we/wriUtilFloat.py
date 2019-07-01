#!/usr/bin/env python3.5
import genericIO
import SepVector
import Hypercube
import numpy as np
import time
import sys
import os

# operators
import Acoustic_iso_float_we
import TruncateSpatialReg
import SpaceInterpFloat
#import PadTruncateSourceFloat
import pyOperator as Op


def forcing_term_op_init(args):

	# Bullshit stuff
	io=genericIO.pyGenericIO.ioModes(args)
	ioDef=io.getDefaultIO()
	parObject=ioDef.getParamObj()

	# Interp operator init
	zCoord,xCoord,centerHyper = SpaceInterpFloat.space_interp_init_source(args)

	#interp operator instantiate
	#check which source injection interp method
	sourceInterpMethod = parObject.getString("sourceInterpMethod","linear")
	sourceInterpNumFilters = parObject.getInt("sourceInterpNumFilters",4)
	nt = parObject.getInt("nts")
	spaceInterpOp = SpaceInterpFloat.space_interp(zCoord,xCoord,centerHyper,nt,sourceInterpMethod,sourceInterpNumFilters)


	# pad truncate init
	dt = parObject.getFloat("dts",0.0)
	nExp = parObject.getInt("nExp")
	tAxis=Hypercube.axis(n=nt,o=0.0,d=dt)
	wfldAxis=Hypercube.axis(n=5,o=0.0,d=1)
	regSourceAxis=Hypercube.axis(n=spaceInterpOp.getNDeviceReg(),o=0.0,d=1)
	irregSourceAxis=Hypercube.axis(n=spaceInterpOp.getNDeviceIrreg(),o=0.0,d=1)
	regSourceHyper=Hypercube.hypercube(axes=[regSourceAxis,wfldAxis,tAxis])
	irregSourceHyper=Hypercube.hypercube(axes=[irregSourceAxis,wfldAxis,tAxis])
	regWfldHyper=Hypercube.hypercube(axes=[centerHyper.getAxis(1),centerHyper.getAxis(2),wfldAxis,tAxis])

	input = SepVector.getSepVector(irregSourceHyper,storage="dataFloat")
	padTruncateDummyModel = SepVector.getSepVector(regSourceHyper,storage="dataFloat")
	padTruncateDummyData = SepVector.getSepVector(regWfldHyper,storage="dataFloat")
	sourceGridPositions = spaceInterpOp.getRegPosUniqueVector()

	padTruncateSourceOp = PadTruncateSourceFloat.pad_truncate_source(padTruncateDummyModel,padTruncateDummyData,sourceGridPositions)

	#stagger op
	# staggerDummyModel = SepVector.getSepVector(padTruncateDummyData.getHyper(),storage="dataFloat")
	# output = SepVector.getSepVector(padTruncateDummyData.getHyper(),storage="dataFloat")
	# wavefieldStaggerOp=StaggerFloat.stagger_wfld(staggerDummyModel,output)

	#chain operators
	spaceInterpOp.setDomainRange(padTruncateDummyModel,input)
	spaceInterpOp = Op.Transpose(spaceInterpOp)
	PK_adj = Op.ChainOperator(spaceInterpOp,padTruncateSourceOp)
	#SPK_adj = Op.ChainOperator(PK_adj,wavefieldStaggerOp)

	#read in source
	# waveletFloat = SepVector.getSepVector(SPK_adj.getDomain().getHyper(),storage="dataFloat")
	priorData = SepVector.getSepVector(PK_adj.getRange().getHyper(),storage="dataFloat")
	priorModel = SepVector.getSepVector(PK_adj.getDomain().getHyper(),storage="dataFloat")
	waveletFile=parObject.getString("wavelet")
	waveletFloat=genericIO.defaultIO.getVector(waveletFile)
	waveletSMat=waveletFloat.getNdArray()
	waveletSMatT=np.transpose(waveletSMat)
	priorModelMat=priorModel.getNdArray()
	#loop over irreg grid sources and set each to wavelet
	for iShot in range(irregSourceAxis.n):
		priorModelMat[:,:,iShot] = waveletSMatT

	PK_adj.forward(False,priorModel,priorData)

	return PK_adj,priorData

#
def data_extraction_reg_op_init(args):

	# Bullshit stuff
	io=genericIO.pyGenericIO.ioModes(args)
	ioDef=io.getDefaultIO()
	parObject=ioDef.getParamObj()

	# Time Axis
	nts=parObject.getInt("nts",-1)
	ots=parObject.getFloat("ots",0.0)
	dts=parObject.getFloat("dts",-1.0)
	timeAxis=Hypercube.axis(n=nts,o=ots,d=dts)

	# z Axis model
	nz=parObject.getInt("nz",-1)
	oz=parObject.getFloat("oz",-1.0)
	dz=parObject.getFloat("dz",-1.0)
	zAxis=Hypercube.axis(n=nz,o=oz,d=dz)

	# x axis model
	nx=parObject.getInt("nx",-1)
	ox=parObject.getFloat("ox",-1.0)
	dx=parObject.getFloat("dx",-1.0)
	xAxis=Hypercube.axis(n=nx,o=ox,d=dx)

	# Allocate model
	modelHyper=Hypercube.hypercube(axes=[zAxis,xAxis,timeAxis])
	modelFloat=SepVector.getSepVector(modelHyper,storage="dataFloat")

	# z Axis data
	nzData=parObject.getInt("nzData",-1)
	ozData=parObject.getFloat("ozData",-1.0)
	dzData=parObject.getFloat("dzData",-1.0)
	zAxisData=Hypercube.axis(n=nzData,o=ozData,d=dzData)

	# x axis data
	nxData=parObject.getInt("nxData",-1)
	oxData=parObject.getFloat("oxData",-1.0)
	dxData=parObject.getFloat("dxData",-1.0)
	xAxisData=Hypercube.axis(n=nxData,o=oxData,d=dxData)

	# Allocate data
	dataHyper=Hypercube.hypercube(axes=[zAxisData,xAxisData,timeAxis])
	dataFloat = SepVector.getSepVector(dataHyper,storage="dataFloat")

	# init op
	op=TruncateSpatialReg.sampleDataReg(modelFloat,dataFloat)

	#apply forward
	return modelFloat,dataFloat,op
#
# def data_extraction_op_init(args):
#
# 	# Bullshit stuff
# 	io=genericIO.pyGenericIO.ioModes(args)
# 	ioDef=io.getDefaultIO()
# 	parObject=ioDef.getParamObj()
#
# 	# Interp operator init
# 	zCoord,xCoord,centerHyper = SpaceInterpMulti.space_interp_init_rec(args)
#
# 	# Horizontal axis
# 	nx=centerHyper.getAxis(2).n
# 	dx=centerHyper.getAxis(2).d
# 	ox=centerHyper.getAxis(2).o
#
# 	# Vertical axis
# 	nz=centerHyper.getAxis(1).n
# 	dz=centerHyper.getAxis(1).d
# 	oz=centerHyper.getAxis(1).o
#
# 	#interp operator instantiate
# 	#check which rec injection interp method
# 	recInterpMethod = parObject.getString("recInterpMethod","linear")
# 	recInterpNumFilters = parObject.getInt("recInterpNumFilters",4)
# 	nt = parObject.getInt("nts")
# 	spaceInterpOp = SpaceInterpFloat.space_interp(zCoord,xCoord,centerHyper,nt,recInterpMethod,recInterpNumFilters)
#
# 	# pad truncate init
# 	dts = parObject.getFloat("dts",0.0)
# 	nExp = parObject.getInt("nExp")
# 	tAxis=Hypercube.axis(n=nt,o=0.0,d=dts)
# 	regRecAxis=Hypercube.axis(n=spaceInterpOp.getNDeviceReg(),o=0.0,d=1)
# 	oxReceiver=parObject.getInt("oReceiver")-1+parObject.getInt("fat")
# 	dxReceiver=parObject.getInt("dReceiver")
# 	irregRecAxis=Hypercube.axis(n=spaceInterpOp.getNDeviceIrreg(),o=ox+oxReceiver*dx,d=dxReceiver*dx)
# 	regRecHyper=Hypercube.hypercube(axes=[regRecAxis,tAxis])
# 	irregRecHyper=Hypercube.hypercube(axes=[irregRecAxis,tAxis])
# 	regWfldHyper=Hypercube.hypercube(axes=[centerHyper.getAxis(1),centerHyper.getAxis(2),tAxis])
#
# 	output = SepVector.getSepVector(irregRecHyper,storage="dataFloat")
# 	padTruncateDummyModel = SepVector.getSepVector(regRecHyper,storage="dataFloat")
# 	padTruncateDummyData = SepVector.getSepVector(regWfldHyper,storage="dataFloat")
# 	recGridPositions = spaceInterpOp.getRegPosUniqueVector()
# 	padTruncateRecOp = PadTruncateSourceFloat.pad_truncate_source(padTruncateDummyModel,padTruncateDummyData,recGridPositions)
# 	padTruncateRecOp = Op.Transpose(padTruncateRecOp)
#
# 	# #stagger op
# 	# staggerDummyModel = SepVector.getSepVector(padTruncateDummyData.getHyper(),storage="dataFloat")
# 	# input = SepVector.getSepVector(padTruncateDummyData.getHyper(),storage="dataFloat")
# 	# wavefieldStaggerOp=StaggerFloat.stagger_wfld(staggerDummyModel,input)
# 	# wavefieldStaggerOp=Op.Transpose(wavefieldStaggerOp)
#
# 	#chain operators
# 	spaceInterpOp.setDomainRange(padTruncateDummyModel,output)
# 	#spaceInterpOp = Op.Transpose(spaceInterpOp)
# 	# P_adjS_adj = Op.ChainOperator(wavefieldStaggerOp,padTruncateRecOp)
# 	KP_adj = Op.ChainOperator(P_adj,spaceInterpOp)
#
# 	#apply forward
# 	return KP_adj
