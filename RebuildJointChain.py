# ----------------------------------------------------------------------------------------------------------------------
"""

	REBUILDJOINTCHAIN.PY
	Dynamically change length of selected joint chain.

	import RebuildJointChain
	RebuildJointChain.run()

	Antony Thomas

"""
# ----------------------------------------------------------------------------------------------------------------------

from maya import OpenMaya as om
import maya.cmds as mc

from PySide2 import QtGui, QtCore, QtWidgets


class rebuildUI(QtWidgets.QWidget):
	def __init__(self):
		super(rebuildUI, self).__init__()

		try:
			slider_ui.deleteLater()
		except (NameError, RuntimeError):
			pass

		mc.undoInfo(openChunk=True)

		self.jnts = mc.ls(sl=True, type='joint')
		if len(self.jnts) < 3:
			mc.confirmDialog(t='Yeah, nah bro.', m="try select a chain of at least 3 joints.")
			raise ValueError('--Not enough joints selected. A chain of at least 3 joints is required.')

		self.name = self.jnts[0]

		# if joint chain has a parent or children, save that information to re-construct the hierarchy later.
		self.topParent = mc.listRelatives(self.jnts[0], parent=True)
		self.children = {}

		# find any children not apart of selected joint chain, un-parent and add to self.children
		for i, jnt in enumerate(self.jnts):
			children = mc.listRelatives(jnt, children=True)
			if children:
				for child in children:
					try:
						if child != self.jnts[i + 1].split('|')[-1]:
							self.children[child] = float(i+1) / float(len(self.jnts))
							mc.parent(child, world=True)
					except IndexError:
						self.children[child] = float(i+1) / float(len(self.jnts))
						mc.parent(child, world=True)

		# create function sets for the curve
		self.curvFn = om.MFnNurbsCurve()
		transformFn = om.MFnTransform()

		# create transform
		self.transformMOb = transformFn.create()
		transformFn.setName('RebuildJointChain_curv')

		# create cv and knot arrays
		cvs = om.MPointArray()
		knot_vector = om.MDoubleArray()

		for jnt in self.jnts:
			jnt_wrld_vect = mc.xform(jnt, q=True, t=True, ws=True)
			cvs.append(om.MPoint(jnt_wrld_vect[0], jnt_wrld_vect[1], jnt_wrld_vect[2]))

		# calculate knot vector
		degree = 2
		nspans = cvs.length() - degree
		nknots = nspans + 2 * degree - 1

		for i in range(degree - 1):
			knot_vector.append(0.0)
		for j in range(nknots - (2 * degree) + 2):
			knot_vector.append(j)
		for k in range(degree - 1):
			knot_vector.append(j)

		# create curve
		self.curvFn.create(cvs, knot_vector, degree, om.MFnNurbsCurve.kOpen, False, True, transformFn.object())

		# get mouse position
		point = QtGui.QCursor.pos()

		# create ui
		self.setWindowFlags(QtCore.Qt.FramelessWindowHint)
		self.setGeometry(point.x(), point.y(), 170, 30)

		self.installEventFilter(self)

		self.mainLayout = QtWidgets.QHBoxLayout(self)

		self.slider = QtWidgets.QSlider(self)
		self.slider.setOrientation(QtCore.Qt.Orientation.Horizontal)
		self.slider.setRange(2, 25)
		self.slider.setValue(len(self.jnts))

		self.mainLayout.addWidget(self.slider)

		self.jointField = QtWidgets.QSpinBox(self)
		self.jointField.setRange(2, 150)
		self.jointField.setValue(len(self.jnts))
		self.jointField.setMaximumWidth(30)
		self.jointField.setButtonSymbols(QtWidgets.QAbstractSpinBox.NoButtons)

		self.mainLayout.addWidget(self.jointField)

		self.slider.valueChanged.connect(self.slider_changed)
		self.jointField.valueChanged.connect(self.text_changed)

		self.show()

	def eventFilter(self, object, event):
		# Intercept de-activating the window to delete ui, delete the curve, and reconstruct hierarchy.
		if event.type() == QtCore.QEvent.WindowDeactivate:
			# Delete curve
			dgMod = om.MDagModifier()
			dgMod.deleteNode(self.transformMOb)
			dgMod.doIt()

			self.jnts.reverse()
			# Orient and parent joints.
			if not mc.listRelatives(self.jnts[0], parent=True):
				for i in range(len(self.jnts) - 1):
					mc.delete(mc.aimConstraint(self.jnts[i], self.jnts[i + 1], mo=False))
					mc.parent(self.jnts[i], self.jnts[i + 1])

				for axis in ['X', 'Y', 'Z']:
					mc.setAttr('{}.jointOrient{}'.format(self.jnts[0], axis), 0)

			# Re-construct the dag hierarchy.
			for child, position in self.children.iteritems():
				try:
					mc.parent(child, self.jnts[int(round((len(self.jnts)) * (1 - position)))])
				except (RuntimeError, ValueError):
					pass
			if self.topParent:
				try:
					mc.parent(self.jnts[-1], self.topParent)
				except (RuntimeError, ValueError):
					pass

			mc.undoInfo(closeChunk=True)
			slider_ui.deleteLater()
		return 0

	def slider_changed(self, value):
		self.jointField.setValue(value)

	def text_changed(self, value):
		if value < 26:
			self.slider.setValue(value)

		self.create_joints_on_curve(value)

	def create_joints_on_curve(self, num):
		# This is where the magic happens oo yea.
		mc.delete(self.jnts)

		jnt_ls = []
		for i in range(num):
			parameter = self.curvFn.findParamFromLength(self.curvFn.length() * (1.0 / (num - 1)) * i)
			point = om.MPoint()
			self.curvFn.getPointAtParam(parameter, point)
			jnt_ls.append(mc.createNode("joint", name=self.name))
			mc.xform(jnt_ls[i], t=[point.x, point.y, point.z])

		self.jnts = jnt_ls


def run():
	global slider_ui
	slider_ui = rebuildUI()
