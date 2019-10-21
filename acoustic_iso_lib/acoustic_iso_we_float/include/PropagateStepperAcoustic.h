#pragma once
#include <operator.h>
#include <float2DReg.h>
#include <float3DReg.h>
#include <C4.h>
#include <C5.h>
#include <C6.h>
#include <BoundaryCondition.h>
#include <PropagateStepper.h>

using namespace giee;

namespace waveform {
class PropagateStepperAcoustic : public waveform::PropagateStepper {
public:

  PropagateStepperAcoustic(
    const std::shared_ptr<SEP::float2DReg>           model,
    const std::shared_ptr<SEP::float2DReg>           data,
    const std::shared_ptr<SEP::float2DReg>           velPadded,
    const std::shared_ptr<SEP::float3DReg>           sourceCube,
    const std::shared_ptr<waveform::BoundaryCondition>BC,
    const int                                         velPadx,
    const int                                         velPadz
    );

  virtual void forward(const bool                         add,
                       const std::shared_ptr<SEP::Vector>model,
                       std::shared_ptr<SEP::Vector>      data);

  virtual void adjoint(const bool                         add,
                       std::shared_ptr<SEP::Vector>      model,
                       const std::shared_ptr<SEP::Vector>data);

private:

  std::shared_ptr<Operator>_C4;
  std::shared_ptr<Operator>_C5;
  std::shared_ptr<Operator>_C6;
  std::shared_ptr<SEP::float2DReg>_pOld;
  std::shared_ptr<SEP::float3DReg>_sourceCube;
  std::shared_ptr<SEP::float2DReg>_sourceCur;
  int _it;
};
}

// PURELY VIRTUAL