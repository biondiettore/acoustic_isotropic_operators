#ifndef BORN_EXT_GPU_H
#define BORN_EXT_GPU_H 1

#include <string>
#include <tbb/tbb.h>
#include <tbb/blocked_range.h>
#include <tbb/parallel_for.h>
#include <tbb/parallel_reduce.h>
#include "float2DReg.h"
#include "float3DReg.h"
#include "ioModes.h"
#include "deviceGpu.h"
#include "fdParam.h"
#include "seismicOperator2D.h"
#include "interpTimeLinTbb.h"
#include "secondTimeDerivative.h"
#include "BornExtShotsGpuFunctions.h"

using namespace SEP;

class BornExtGpu : public seismicOperator2D<SEP::float3DReg, SEP::float2DReg> {

	private:

		std::shared_ptr<float3DReg> _srcWavefield, _secWavefield;

	public:

		/* Overloaded constructor */
		BornExtGpu(std::shared_ptr<SEP::float2DReg> vel, std::shared_ptr<paramObj> par, int nGpu, int iGpu, int iGpuId, int iGpuAlloc);

		/* Mutators */
		void setAllWavefields(int wavefieldFlag); // Allocates all wavefields assocaited with a seismic operator

		/* QC */
		bool checkParfileConsistency(const std::shared_ptr<SEP::float3DReg> model, const std::shared_ptr<SEP::float2DReg> data) const;

		/* FWD - ADJ */
		void forward(const bool add, const std::shared_ptr<float3DReg> model, std::shared_ptr<float2DReg> data) const;
		void adjoint(const bool add, std::shared_ptr<float3DReg> model, const std::shared_ptr<float2DReg> data) const;

		/* Destructor */
		~BornExtGpu(){};

		/* Accessors */
		std::shared_ptr<float3DReg> getSrcWavefield() { return _srcWavefield; }
		std::shared_ptr<float3DReg> getSecWavefield() { return _secWavefield; } // Returns the "secondary" wavefield (either scattered for Born forward or receiver for Born adjoint)

};

#endif
