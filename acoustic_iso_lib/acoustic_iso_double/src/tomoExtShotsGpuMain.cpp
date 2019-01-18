#include <omp.h>
#include <iostream>
#include <time.h>
#include <stdlib.h>
#include <stdio.h>
#include <tbb/tbb.h>
#include <tbb/blocked_range.h>
#include <tbb/parallel_for.h>
#include <tbb/parallel_reduce.h>
#include "float1DReg.h"
#include "float2DReg.h"
#include "float3DReg.h"
#include "double1DReg.h"
#include "double2DReg.h"
#include "double3DReg.h"
#include "ioModes.h"
#include "deviceGpu.h"
#include "tomoExtShotsGpu.h"
#include <vector>

using namespace SEP;

int main(int argc, char **argv) {

	/************************************** Main IO *************************************/
	ioModes modes(argc, argv);
	std::shared_ptr <SEP::genericIO> io = modes.getDefaultIO();
	std::shared_ptr <paramObj> par = io->getParamObj();
	int adj = par->getInt("adj", 0);
	int saveWavefield = par->getInt("saveWavefield");
	int dotProd = par->getInt("dotProd", 0);
	int nShot = par->getInt("nShot");

	if (adj == 0 && dotProd == 0){
		std::cout << " " << std::endl;
		std::cout << "-------------------------------------------------------------------" << std::endl;
		std::cout << "------------------ Running extended tomo forward ------------------" << std::endl;
		std::cout << "-------------------------------------------------------------------" << std::endl;
		std::cout << " " << std::endl;
	}

	if (adj == 1 && dotProd == 0){
		std::cout << " " << std::endl;
		std::cout << "-------------------------------------------------------------------" << std::endl;
		std::cout << "------------------ Running extended tomo adjoint ------------------" << std::endl;
		std::cout << "-------------------------------------------------------------------" << std::endl;
		std::cout << " " << std::endl;
	}
	if (dotProd == 1){
		std::cout << " " << std::endl;
		std::cout << "-------------------------------------------------------------------" << std::endl;
		std::cout << "------------------------ Running dot product test -----------------" << std::endl;
		std::cout << "-------------------------------------------------------------------" << std::endl;
		std::cout << " " << std::endl;
	}


	/* Model and data declaration */
	std::shared_ptr<float2DReg> sourcesSignalTempFloat;
	std::shared_ptr<double2DReg> sourcesSignalTempDouble;
	std::shared_ptr<double2DReg> model1Double, model2Double; // Model
	std::shared_ptr<float2DReg> model1Float, model2Float;
	std::shared_ptr<double3DReg> data1Double, data2Double; // Data
	std::shared_ptr<float3DReg> data1Float, data2Float;
	std::shared_ptr <genericRegFile> sourcesFile, model1File, model2File, data1File, data2File, sourcesSignalsFile;
	std::shared_ptr <hypercube> model1Hyper, data1Hyper;

	/* Read time parameters */
	int nts = par->getInt("nts");
	double dts = par->getFloat("dts", 0.0);
	int sub = par->getInt("sub");
	axis timeAxisCoarse = axis(nts, 0.0, dts);
	int ntw = (nts - 1) * sub + 1;
	double dtw = dts / double(sub);
	axis timeAxisFine = axis(ntw, 0.0, dtw);

	/* Read extension parameters */
	axis extAxis;
	std::string extension = par->getString("extension", "none");
	int nExt = par->getInt("nExt", 1);
	if (nExt%2 == 0){std::cout << "**** ERROR: Length of extended axis must be an uneven number ****" << std::endl; assert(1==2);}
	int hExt = (nExt-1)/2;
	if (extension == "time"){
		double dExt = par->getFloat("dExt", dts);
		double oExt = par->getFloat("oExt", -dExt*hExt);
		extAxis = axis(nExt, oExt, dExt);
	} else {
		double dExt = par->getFloat("dExt", par->getFloat("dx", -1.0));
		double oExt = par->getFloat("oExt", -dExt*hExt);
		extAxis = axis(nExt, oExt, dExt);
	}

	/* Read padding parameters */
	int zPadMinus = par->getInt("zPadMinus");
	int zPadPlus = par->getInt("zPadPlus");
	int xPadMinus = par->getInt("xPadMinus");
	int xPadPlus = par->getInt("xPadPlus");
	int fat = par->getInt("fat");

	/********************************* Velocity model ***********************************/
	/* Read velocity (includes the padding + FAT) */
	std::shared_ptr<SEP::genericRegFile> velFile = io->getRegFile("vel",usageIn);
	std::shared_ptr<SEP::hypercube> velHyper = velFile->getHyper();
	std::shared_ptr<SEP::float2DReg> velFloat(new SEP::float2DReg(velHyper));
	std::shared_ptr<SEP::double2DReg> velDouble(new SEP::double2DReg(velHyper));
	velFile->readFloatStream(velFloat);
	int nz = velFloat->getHyper()->getAxis(1).n;
	double oz = velFloat->getHyper()->getAxis(1).o;
	double dz = velFloat->getHyper()->getAxis(1).d;
	int nx = velFloat->getHyper()->getAxis(2).n;
	double ox = velFloat->getHyper()->getAxis(2).o;
	double dx = velFloat->getHyper()->getAxis(2).d;
	for (int ix = 0; ix < nx; ix++) {
		for (int iz = 0; iz < nz; iz++) {
			(*velDouble->_mat)[ix][iz] = (*velFloat->_mat)[ix][iz];
		}
	}

	/******************************* Extended reflectivity ******************************/
	/* Read velocity (includes the padding + FAT) */
	std::shared_ptr<SEP::genericRegFile> reflectivityExt1File = io->getRegFile("reflectivity",usageIn);
	std::shared_ptr<SEP::hypercube> reflectivityExt1Hyper = reflectivityExt1File->getHyper();
	if (reflectivityExt1Hyper->getNdim() == 2){ // Case where reflectivity is not extended
		axis a(1);
		reflectivityExt1Hyper->addAxis(a);
	}
	std::shared_ptr<SEP::float3DReg> reflectivityExt1Float(new SEP::float3DReg(reflectivityExt1Hyper));
	std::shared_ptr<SEP::double3DReg> reflectivityExt1Double(new SEP::double3DReg(reflectivityExt1Hyper));
	reflectivityExt1File->readFloatStream(reflectivityExt1Float);

	#pragma omp parallel for
	for (int iExt=0; iExt<reflectivityExt1Hyper->getAxis(3).n; iExt++) {
		for (int ix=0; ix<reflectivityExt1Hyper->getAxis(2).n; ix++) {
			for (int iz=0; iz<reflectivityExt1Hyper->getAxis(1).n; iz++){
				(*reflectivityExt1Double->_mat)[iExt][ix][iz] = (*reflectivityExt1Float->_mat)[iExt][ix][iz];
			}
		}
	}

	/********************************* Create sources vector ****************************/
	int nzSource = 1;
	int ozSource = par->getInt("zSource") - 1 + zPadMinus + fat;
	int dzSource = 1;
	int nxSource = 1;
	int oxSource = par->getInt("xSource") - 1 + xPadMinus + fat;
	int dxSource = 1;
	int spacingShots = par->getInt("spacingShots", spacingShots);
	axis sourceAxis(nShot, ox+oxSource*dx, spacingShots*dx);
	std::vector<std::shared_ptr<deviceGpu>> sourcesVector;
	for (int iShot; iShot<nShot; iShot++){
		std::shared_ptr<deviceGpu> sourceDevice(new deviceGpu(nzSource, ozSource, dzSource, nxSource, oxSource, dxSource, velDouble, nts));
		sourcesVector.push_back(sourceDevice);
		oxSource = oxSource + spacingShots;
	}
	axis shotAxis = axis(nShot, oxSource, dxSource);

	/********************************* Create receivers vector **************************/
	int nzReceiver = 1;
	int ozReceiver = par->getInt("depthReceiver") - 1 + zPadMinus + fat;
	int dzReceiver = 1;
	int nxReceiver = par->getInt("nReceiver");
	int oxReceiver = par->getInt("oReceiver") - 1 + xPadMinus + fat;
	int dxReceiver = par->getInt("dReceiver");
	axis receiverAxis(nxReceiver, ox+oxReceiver*dx, dxReceiver*dx);
	std::vector<std::shared_ptr<deviceGpu>> receiversVector;
	int nRecGeom = 1; // Constant receivers' geometry
	for (int iRec; iRec<nRecGeom; iRec++){
		std::shared_ptr<deviceGpu> recDevice(new deviceGpu(nzReceiver, ozReceiver, dzReceiver, nxReceiver, oxReceiver, dxReceiver, velDouble, nts));
		receiversVector.push_back(recDevice);
	}

	/******************************* Create sources signals vector **********************/
	// Read sources signals file - we use one identical wavelet for all shots
	sourcesSignalsFile = io->getRegFile(std::string("sources"),usageIn);
	std::shared_ptr <hypercube> sourcesSignalsHyper = sourcesSignalsFile->getHyper();
	std::vector<std::shared_ptr<double2DReg>> sourcesSignalsVector;
	if (sourcesSignalsHyper->getNdim() == 1){
		axis a(1);
		sourcesSignalsHyper->addAxis(a);
	}
	sourcesSignalTempFloat = std::make_shared<float2DReg>(sourcesSignalsHyper);
	sourcesSignalTempDouble = std::make_shared<double2DReg>(sourcesSignalsHyper);
	sourcesSignalsFile->readFloatStream(sourcesSignalTempFloat);
	for (int its=0; its<nts; its++){(*sourcesSignalTempDouble->_mat)[0][its] = (*sourcesSignalTempFloat->_mat)[0][its];}
	sourcesSignalsVector.push_back(sourcesSignalTempDouble);

	/*********************************** Allocation *************************************/

	/* Forward propagation */
	if (adj == 0) {

		/* Allocate and read model */
		model1File = io->getRegFile(std::string("model1"),usageIn);
		std::shared_ptr <hypercube> model1Hyper = model1File->getHyper();
		model1Float = std::make_shared<float2DReg>(model1Hyper);
		model1Double = std::make_shared<double2DReg>(model1Hyper);
		model1File->readFloatStream(model1Float);
		for (int ix=0; ix<model1Hyper->getAxis(2).n; ix++) {
			for (int iz=0; iz<model1Hyper->getAxis(1).n; iz++) {
				(*model1Double->_mat)[ix][iz] = (*model1Float->_mat)[ix][iz];
			}
		}

		/* Data allocation */
		std::shared_ptr<hypercube> data1Hyper(new hypercube(sourcesSignalsHyper->getAxis(1), receiverAxis, sourceAxis));
		data1Double = std::make_shared<double3DReg>(data1Hyper);
		data1Float = std::make_shared<float3DReg>(data1Hyper);

		/* Files shits */
		data1File = io->getRegFile(std::string("data1"), usageOut);
		data1File->setHyper(data1Hyper);
		data1File->writeDescription();

	}

	/* Adjoint propagation */
	if (adj == 1) {

		/* Allocate and read data */
		data1File = io->getRegFile(std::string("data1"),usageIn);
		std::shared_ptr <hypercube> data1Hyper = data1File->getHyper();

		// Case where only one receiver and 1 shot
		if (data1Hyper->getNdim() == 1){
			axis a(1);
			data1Hyper->addAxis(a);
			data1Hyper->addAxis(a);
		}

		// Case where only multiple receivers and 1 shot
		if (data1Hyper->getNdim() == 2){
			axis a(1);
			data1Hyper->addAxis(a);
		}

		data1Float = std::make_shared<float3DReg>(data1Hyper);
		data1Double = std::make_shared<double3DReg>(data1Hyper);
		data1File->readFloatStream(data1Float);
		for (int iShot=0; iShot<nShot; iShot++){
			for (int ix=0; ix<data1Hyper->getAxis(2).n; ix++) {
				for (int iz=0; iz<data1Hyper->getAxis(1).n; iz++) {
					(*data1Double->_mat)[iShot][ix][iz] = (*data1Float->_mat)[iShot][ix][iz];
				}
			}
		}

		/* Allocate and read model */
		std::shared_ptr<hypercube> model1Hyper = velHyper;
		model1Float = std::make_shared<float2DReg>(model1Hyper);
		model1Double = std::make_shared<double2DReg>(model1Hyper);

		/* Stupid files shits */
		model1File = io->getRegFile(std::string("model1"),usageOut);
		model1File->setHyper(model1Hyper);
		model1File->writeDescription();

	}

	/* Wavefields */
	std::shared_ptr<double3DReg> srcWavefield1Double, srcWavefield2Double, secWavefield1Double, secWavefield2Double;
	std::shared_ptr<float3DReg> srcWavefield1Float, srcWavefield2Float, secWavefield1Float, secWavefield2Float;
	std::shared_ptr<genericRegFile> srcWavefield1File = io->getRegFile(std::string("srcWavefield1"), usageOut);
	std::shared_ptr<genericRegFile> secWavefield1File = io->getRegFile(std::string("secWavefield1"), usageOut);
	std::shared_ptr<genericRegFile> secWavefield2File = io->getRegFile(std::string("secWavefield2"), usageOut);

	/************************************************************************************/
	/******************************** SIMULATIONS ***************************************/
	/************************************************************************************/

	/* Create tomo extended object */
	std::shared_ptr<tomoExtShotsGpu> object1(new tomoExtShotsGpu(velDouble, par, sourcesVector, sourcesSignalsVector, receiversVector, reflectivityExt1Double));

	/********************************** FORWARD *****************************************/
	if (adj == 0 && dotProd ==0) {

		if (saveWavefield == 1){
			object1->forwardWavefield(false, model1Double, data1Double);
		} else {
			object1->forward(false, model1Double, data1Double);
		}

		// Data
		for (int iShot=0; iShot<nShot; iShot++){
			for (int ix=0; ix<data1Double->getHyper()->getAxis(2).n; ix++) {
				for (int iz=0; iz<data1Double->getHyper()->getAxis(1).n; iz++) {
					(*data1Float->_mat)[iShot][ix][iz] = (*data1Double->_mat)[iShot][ix][iz];
				}
			}
		}
		data1File->writeFloatStream(data1Float);

		/* Wavefield */
		if (saveWavefield == 1){
			std::shared_ptr<hypercube> wavefield1Hyper(new hypercube(velFloat->getHyper()->getAxis(1), velFloat->getHyper()->getAxis(2), timeAxisCoarse));
			srcWavefield1Double = object1->getSrcWavefield(); // Source wavefield
			secWavefield1Double = object1->getSecWavefield1(); // Forward first scattered wavefield 
			secWavefield2Double = object1->getSecWavefield2(); // Forward second scattered wavefield
			srcWavefield1Float = std::make_shared<float3DReg>(srcWavefield1Double->getHyper());
			secWavefield1Float = std::make_shared<float3DReg>(srcWavefield1Double->getHyper());
			secWavefield2Float = std::make_shared<float3DReg>(srcWavefield1Double->getHyper());

			#pragma omp parallel for
			for (int its = 0; its < nts; its++){
				for (int ix = 0; ix < nx; ix++){
					for (int iz = 0; iz < nz; iz++){
						(*srcWavefield1Float->_mat)[its][ix][iz] = (*srcWavefield1Double->_mat)[its][ix][iz];
						(*secWavefield1Float->_mat)[its][ix][iz] = (*secWavefield1Double->_mat)[its][ix][iz];
						(*secWavefield2Float->_mat)[its][ix][iz] = (*secWavefield2Double->_mat)[its][ix][iz];
					}
				}
			}

			// Write source wavefield
			srcWavefield1File->setHyper(wavefield1Hyper);
			srcWavefield1File->writeDescription();
			srcWavefield1File->writeFloatStream(srcWavefield1Float);

			// Write scattered wavefield #1
			secWavefield1File->setHyper(wavefield1Hyper);
			secWavefield1File->writeDescription();
			secWavefield1File->writeFloatStream(secWavefield1Float);

			// Write scattered wavefield #2
			secWavefield2File->setHyper(wavefield1Hyper);
			secWavefield2File->writeDescription();
			secWavefield2File->writeFloatStream(secWavefield2Float);

		}
	}

	/********************************** ADJOINT *****************************************/
	if (adj == 1 && dotProd ==0) {

		if (saveWavefield == 1){
			object1->adjointWavefield(false, model1Double, data1Double);
		} else {
			object1->adjoint(false, model1Double, data1Double);
		}

		// Model
		for (int ix=0; ix<model1Double->getHyper()->getAxis(2).n; ix++) {
			for (int iz=0; iz<model1Double->getHyper()->getAxis(1).n; iz++) {
				(*model1Float->_mat)[ix][iz] = (*model1Double->_mat)[ix][iz];
			}
		}
		model1File->writeFloatStream(model1Float);

		/* Wavefield */
		if (saveWavefield == 1){
			std::shared_ptr<hypercube> wavefield1Hyper(new hypercube(velFloat->getHyper()->getAxis(1), velFloat->getHyper()->getAxis(2), timeAxisCoarse));
			srcWavefield1Double = object1->getSrcWavefield();
			secWavefield1Double = object1->getSecWavefield1();
			secWavefield2Double = object1->getSecWavefield2();
			srcWavefield1Float = std::make_shared<float3DReg>(srcWavefield1Double->getHyper()); // Source wavefield
			secWavefield1Float = std::make_shared<float3DReg>(srcWavefield1Double->getHyper()); // Receiver wavefield
			secWavefield2Float = std::make_shared<float3DReg>(srcWavefield1Double->getHyper()); // Scattered (forward/adjoint) wavefield
			for (int its = 0; its < nts; its++){
				for (int ix = 0; ix < nx; ix++){
					for (int iz = 0; iz < nz; iz++){
						(*srcWavefield1Float->_mat)[its][ix][iz] = (*srcWavefield1Double->_mat)[its][ix][iz];
						(*secWavefield1Float->_mat)[its][ix][iz] = (*secWavefield1Double->_mat)[its][ix][iz];
						(*secWavefield2Float->_mat)[its][ix][iz] = (*secWavefield2Double->_mat)[its][ix][iz];
					}
				}
			}
			srcWavefield1File->setHyper(wavefield1Hyper);
			srcWavefield1File->writeDescription();
			srcWavefield1File->writeFloatStream(srcWavefield1Float);
			secWavefield1File->setHyper(wavefield1Hyper);
			secWavefield1File->writeDescription();
			secWavefield1File->writeFloatStream(secWavefield1Float);
			secWavefield2File->setHyper(wavefield1Hyper);
			secWavefield2File->writeDescription();
			secWavefield2File->writeFloatStream(secWavefield2Float);
		}

	}

	/* Dot product test */
	if (dotProd == 1) {
		object1->setDomainRange(model1Double, data1Double);
		bool dotprod;
		dotprod = object1->dotTest(true);
	}

	std::cout << " " << std::endl;
	std::cout << "-------------------------------------------------------------------" << std::endl;
	std::cout << "------------------------------ ALL DONE ---------------------------" << std::endl;
	std::cout << "-------------------------------------------------------------------" << std::endl;
	std::cout << " " << std::endl;

	return 0;

}
