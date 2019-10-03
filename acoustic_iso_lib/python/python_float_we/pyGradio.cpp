/*PyBind11 header files*/
#include <pybind11/chrono.h>
#include <pybind11/complex.h>
#include <pybind11/functional.h>
#include <pybind11/pybind11.h>
#include <pybind11/stl.h>
#include <pybind11/iostream.h>
/*Library header files*/
#include "Gradio.h"

namespace py = pybind11;
using namespace SEP;


PYBIND11_MODULE(pyGradio, clsGeneric) {
  //Necessary to redirect std::cout into python stdout
	py::add_ostream_redirect(clsGeneric, "ostream_redirect");

    py::class_<Gradio, std::shared_ptr<Gradio>>(clsGeneric,"Gradio")  //
      .def(py::init<const std::shared_ptr<float2DReg>,const std::shared_ptr<float3DReg>, const std::shared_ptr<float3DReg>>(),"Initlialize Gradio")

      .def("forward",(void (Gradio::*)(const bool, const std::shared_ptr<float2DReg>, std::shared_ptr<float3DReg>)) &Gradio::forward,"Forward")

      .def("adjoint",(void (Gradio::*)(const bool, std::shared_ptr<float2DReg>, const std::shared_ptr<float3DReg>)) &Gradio::adjoint,"Adjoint")

      .def("dotTest",(bool (Gradio::*)(const bool, const float)) &Gradio::dotTest,"Dot-Product Test")

      .def("set_wfld",(bool (Gradio::*)(std::shared_ptr<float3DReg>)) &Gradio::set_wfld,"Dot-Product Test")
    ;

}



