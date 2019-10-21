#pragma once
#include <operator.h>
#include <BoundaryCondition.h>
#include <float2DReg.h>
using namespace giee;
using namespace waveform;

namespace waveform {
class C4 : public Operator {
public:

  C4(
    const std::shared_ptr<SEP::float2DReg>model,
    const std::shared_ptr<SEP::float2DReg>data,
    const std::shared_ptr<SEP::float2DReg>velPadded,
    const int                              velPadx,
    const int                              velPadz,
    const float                            dt
    );

  void forward(const bool                         add,
               const std::shared_ptr<SEP::Vector>model,
               std::shared_ptr<SEP::Vector>      data);

  void adjoint(const bool                         add,
               std::shared_ptr<SEP::Vector>      model,
               const std::shared_ptr<SEP::Vector>data);

private:

  void setWeight();

  std::shared_ptr<SEP::float2DReg>_velPadded;
  int _velPadx, _velPadz;
  double _dt;
  std::shared_ptr<SEP::float2DReg>_aborbWeight;
  double const _absConst = 0.15;
};
}