#!/usr/bin/env python3.5
import genericIO
import SepVector
import Hypercube
import numpy as np
import sys

if __name__ == '__main__':

	# Bullshit stuff
	io=genericIO.pyGenericIO.ioModes(sys.argv)
	ioDef=io.getDefaultIO()
	parObject=ioDef.getParamObj()
	offset=parObject.getString("offset","pos")
	# xShot=parObject.getFloat("xShot") # Shot position [km]
	iShot=parObject.getInt("iShot")
	res=parObject.getInt("res",1) # Flag to determined whether the input model is a predicted data or data residual

	# Read true data
	obsDataFile=parObject.getString("obsIn")
	obsData=genericIO.defaultIO.getVector(obsDataFile,ndims=3)
	obsDataNp=obsData.getNdArray()

	# Read data residuals or predicted data
	modelFile=parObject.getString("model")
	model=genericIO.defaultIO.getVector(modelFile,ndims=4)
	modelNp=model.getNdArray()

	# Iteration
	oIter=model.getHyper().axes[3].o
	dIter=model.getHyper().axes[3].d
	nIter=model.getHyper().axes[3].n
	iterAxis=Hypercube.axis(n=nIter,o=oIter,d=dIter,label="Iteration #")

	# Shot
	oShot=obsData.getHyper().axes[2].o
	dShot=obsData.getHyper().axes[2].d
	nShot=obsData.getHyper().axes[2].n
	oShotGrid=parObject.getInt("xSource")
	dShotGrid=parObject.getInt("spacingShots")

	# Receiver
	oRec=obsData.getHyper().axes[1].o
	dRec=obsData.getHyper().axes[1].d
	nRec=obsData.getHyper().axes[1].n
	recAxis=Hypercube.axis(n=nRec,o=oRec,d=dRec,label="Receivers [km]")

	# Time
	ots=obsData.getHyper().axes[0].o
	dts=obsData.getHyper().axes[0].d
	nts=obsData.getHyper().axes[0].n
	timeAxis=Hypercube.axis(n=nts,o=ots,d=dts,label="Time [s]")

	# Find indices on the "shot grid" and "receiver grid"

	xShot=oShot+dShot*iShot # Shot position [km]
	iShotRecGrid=int((xShot-oRec)/dRec)
	xShotNew=oRec+iShotRecGrid*dRec
	print("xShot=",xShot)
	print("oShot=",oShot)
	print("dShot=",dShot)
	print("iShot=",iShot)
	print("iShotRecGrid=",iShotRecGrid)

	# iShot=int((xShot-oShot)/dShot)
	# iShotRecGrid=oShotGrid+iShot*dShotGrid

	# If user provides residual data instead of predicted data
	if(res==1):
		for iIter in range(nIter):
			modelNp[iIter][iShot][:][:]=modelNp[iIter][iShot][:][:]+obsDataNp[iShot][:][:]

	# Find the number of traces for each side
	if(offset=="pos"):
		nRecNew=nRec-iShotRecGrid-1
	else:
		nRecNew=iShotRecGrid

	# Total number of receivers for the super shot gather
	nRecTotal=2*nRecNew+1

	# Allocate super shot gather
	recNewAxis=Hypercube.axis(n=nRecTotal,o=-nRecNew*dRec,d=dRec,label="Offset [km]")
	iterAxis=Hypercube.axis(n=nIter,o=oIter,d=dIter,label="Iteration #")
	# shotNewAxis=Hypercube.axis(n=1,o=xShotNew,d=1.0)
	superShotGatherHyper=Hypercube.hypercube(axes=[timeAxis,recNewAxis,iterAxis])
	superShotGather=SepVector.getSepVector(superShotGatherHyper)
	superShotGather.scale(0.0)
	superShotGatherNp=superShotGather.getNdArray()

	# Allocate observed data
	obsHyper=Hypercube.hypercube(axes=[timeAxis,recAxis])
	obs=SepVector.getSepVector(obsHyper)
	obsNp=obs.getNdArray()
	predHyper=Hypercube.hypercube(axes=[timeAxis,recAxis,iterAxis])
	pred=SepVector.getSepVector(predHyper)
	predNp=pred.getNdArray()

	# Copy value to super shot gather
	if (offset=="pos"):
		for iIter in range(nIter):
			for iRec in range(nRecNew):
				for its in range(nts):
					superShotGatherNp[iIter][iRec][its]=obsDataNp[iShot][iShotRecGrid+nRecNew-iRec][its]
					superShotGatherNp[iIter][iRec+nRecNew+1][its]=modelNp[iIter][iShot][iShotRecGrid+iRec+1][its]
			superShotGatherNp[iIter][nRecNew][:]=obsDataNp[iShot][iShotRecGrid][:]
			predNp[iIter][:][:]=modelNp[iIter][iShot][:][:]
			# obsNp[iIter][:][:]=obsDataNp[iShot][:][:]

	else:
		for iIter in range(nIter):
			for iRec in range(nRecNew):
				superShotGatherNp[iIter][iRec][:]=obsDataNp[iShot][iRec][:]
				superShotGatherNp[iIter][iRec+nRecNew+1][:]=modelNp[iIter][iShot][iShotRecGrid-iRec-1][:]
			superShotGatherNp[iIter][nRecNew][:]=obsDataNp[iShot][iShotRecGrid][:]
			predNp[iIter][:][:]=modelNp[iIter][iShot][:][:]

	obsNp[:][:]=obsDataNp[iShot][:][:]

	# Write super shot gather
	superShotGatherFile=parObject.getString("data")
	genericIO.defaultIO.writeVector(superShotGatherFile,superShotGather)

	# Write observed shot gather
	obsOutFile=parObject.getString("obsOut")
	genericIO.defaultIO.writeVector(obsOutFile,obs)

	# Write predicted shot gather
	predFile=parObject.getString("pred")
	genericIO.defaultIO.writeVector(predFile,pred)