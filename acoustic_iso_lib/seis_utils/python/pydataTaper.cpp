#include <pybind11/chrono.h>
#include <pybind11/complex.h>
#include <pybind11/functional.h>
#include <pybind11/pybind11.h>
#include <pybind11/stl.h>
#include <pybind11/iostream.h>

#include "dataTaper.h"

namespace py = pybind11;
using namespace SEP;

//Definition of Born operator
PYBIND11_MODULE(pydataTaper, clsGeneric) {

  py::add_ostream_redirect(clsGeneric, "ostream_redirect");

  py::class_<dataTaper, std::shared_ptr<dataTaper>>(clsGeneric,"dataTaper")
      .def(py::init<double,double,double,std::shared_ptr<SEP::hypercube>,std::string>(), "Initialize a dataTaper")

      .def("forward", (void (dataTaper::*)(const bool, const std::shared_ptr<double3DReg>, std::shared_ptr<double3DReg>)) &dataTaper::forward, "Forward")

      .def("adjoint", (void (dataTaper::*)(const bool, const std::shared_ptr<double3DReg>, std::shared_ptr<double3DReg>)) &dataTaper::adjoint, "Adjoint")

  ;
}
