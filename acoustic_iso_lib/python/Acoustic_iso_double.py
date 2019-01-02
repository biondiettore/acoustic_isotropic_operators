#Python module encapsulating PYBIND11 module
#It seems necessary to allow std::cout redirection to screen
import pyAcoustic_iso_double1
import pyAcoustic_iso_double2
import pyAcoustic_iso_double3
import pyOperator as Op


class deviceGpu(pyAcoustic_iso_double1.deviceGpu):
	"""deviceGpu class"""

class nonlinearPropShotsGpu(Op.Operator):
	"""Wrapper encapsulating PYBIND11 module for non-linear propagator"""

	def __init__(self,domain,range,velocity,paramP,sourceVector,receiversVector):
		#Domain = source wavelet
		#Range = recorded data space
		self.setDomainRange(domain,range)
		#Checking if getCpp is present
		if("getCpp" in dir(velocity)):
			velocity = velocity.getCpp()
		if("getCpp" in dir(paramP)):
			paramP = paramP.getCpp()
		self.pyOp = pyAcoustic_iso_double1.nonlinearPropShotsGpu(velocity,paramP,sourceVector,receiversVector)
		return

	def forward(self,add,model,data):
		#Checking if getCpp is present
		if("getCpp" in dir(model)):
			model = model.getCpp()
		if("getCpp" in dir(data)):
			data = data.getCpp()
		with pyAcoustic_iso_double1.ostream_redirect():
			self.pyOp.forward(add,model,data)
		return

	def adjoint(self,add,model,data):
		#Checking if getCpp is present
		if("getCpp" in dir(model)):
			model = model.getCpp()
		if("getCpp" in dir(data)):
			data = data.getCpp()
		with pyAcoustic_iso_double1.ostream_redirect():
			self.pyOp.adjoint(add,model,data)
		return

	def dotTestCpp(self,verb=False,maxError=.00001):
		"""Method to call the Cpp class dot-product test"""
		with pyAcoustic_iso_double1.ostream_redirect():
			result=self.pyOp.dotTest(verb,maxError)
		return result


class BornShotsGpu(Op.Operator):
	"""Wrapper encapsulating PYBIND11 module for Born operator"""

	def __init__(self,domain,range,velocity,paramP,sourceVector,sourcesSignalsVector,receiversVector):
		#Domain = source wavelet
		#Range = recorded data space
		self.setDomainRange(domain,range)
		#Checking if getCpp is present
		if("getCpp" in dir(velocity)):
			velocity = velocity.getCpp()
		if("getCpp" in dir(paramP)):
			paramP = paramP.getCpp()
		if("getCpp" in dir(sourcesSignalsVector)):
			sourcesSignalsVector = sourcesSignalsVector.getCpp()
		self.pyOp = pyAcoustic_iso_double2.BornShotsGpu(velocity,paramP,sourceVector,sourcesSignalsVector,receiversVector)
		return

	def forward(self,add,model,data):
		#Checking if getCpp is present
		if("getCpp" in dir(model)):
			model = model.getCpp()
		if("getCpp" in dir(data)):
			data = data.getCpp()
		with pyAcoustic_iso_double2.ostream_redirect():
			self.pyOp.forward(add,model,data)
		return

	def adjoint(self,add,model,data):
		#Checking if getCpp is present
		if("getCpp" in dir(model)):
			model = model.getCpp()
		if("getCpp" in dir(data)):
			data = data.getCpp()
		with pyAcoustic_iso_double2.ostream_redirect():
			self.pyOp.adjoint(add,model,data)
		return

	def dotTestCpp(self,verb=False,maxError=.00001):
		"""Method to call the Cpp class dot-product test"""
		with pyAcoustic_iso_double2.ostream_redirect():
			result=self.pyOp.dotTest(verb,maxError)
		return result

class BornExtShotsGpu(Op.Operator):
	"""Wrapper encapsulating PYBIND11 module for Extended Born operator"""

	def __init__(self,domain,range,velocity,paramP,sourceVector,sourcesSignalsVector,receiversVector):
		#Domain = source wavelet
		#Range = recorded data space
		self.setDomainRange(domain,range)
		#Checking if getCpp is present
		if("getCpp" in dir(velocity)):
			velocity = velocity.getCpp()
		if("getCpp" in dir(paramP)):
			paramP = paramP.getCpp()
		if("getCpp" in dir(sourcesSignalsVector)):
			sourcesSignalsVector = sourcesSignalsVector.getCpp()
		self.pyOp = pyAcoustic_iso_double3.BornExtShotsGpu(velocity,paramP,sourceVector,sourcesSignalsVector,receiversVector)
		return

	def forward(self,add,model,data):
		#Checking if getCpp is present
		if("getCpp" in dir(model)):
			model = model.getCpp()
		if("getCpp" in dir(data)):
			data = data.getCpp()
		with pyAcoustic_iso_double3.ostream_redirect():
			self.pyOp.forward(add,model,data)
		return

	def adjoint(self,add,model,data):
		#Checking if getCpp is present
		if("getCpp" in dir(model)):
			model = model.getCpp()
		if("getCpp" in dir(data)):
			data = data.getCpp()
		with pyAcoustic_iso_double3.ostream_redirect():
			self.pyOp.adjoint(add,model,data)
		return

	def dotTestCpp(self,verb=False,maxError=.00001):
		"""Method to call the Cpp class dot-product test"""
		with pyAcoustic_iso_double3.ostream_redirect():
			result=self.pyOp.dotTest(verb,maxError)
		return result
