"""
/***************************************************************************
Name                 : Calc Area 2.
Description          : Show the area and length when edit vector layer
Date                 : December, 2021
copyright            : (C) 2021 by Luiz Motta
email                : motta.luiz@gmail.com

 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""

__author__ = 'Luiz Motta'
__date__ = '2021-12-22'
__copyright__ = '(C) 2021, Luiz Motta'
__revision__ = '$Format:%H$'


from qgis.PyQt.QtCore import (
    Qt,
    QObject,
    QEvent,
    QPointF,
    pyqtSlot
)
from qgis.PyQt.QtGui import QFont, QTextDocument

from qgis.core import (
    QgsGeometry,
    QgsMapLayerType, QgsWkbTypes,
    QgsDistanceArea,
    QgsUnitTypes,
    QgsCoordinateTransform,
    QgsProject,
    QgsTextAnnotation, QgsMarkerSymbol, QgsFillSymbol,
)
from qgis.gui import QgsMapTool

import qgis.utils as QgsUtils


class AnnotationCanvas(QObject):
    def __init__(self):
        super().__init__()
        self.annotationManager = QgsProject.instance().annotationManager()
        self.annotationManager.annotationAboutToBeRemoved.connect( self.annotationAboutToBeRemoved )

        self._create() # Create self.annot

    def setText(self, text, pointXY):
        def setFrameDocument():
            font = QFont()
            font.setPointSize(12)
            font.setBold( True )
            td = QTextDocument( text )
            td.setDefaultFont( font )
            self.annot.setFrameOffsetFromReferencePointMm( QPointF(0,0) )
            self.annot.setFrameSize( td.size() )
            self.annot.setDocument( td )

        if not self.annot in self.annotationManager.annotations():
            self._create()
            self.annotationManager.addAnnotation( self.annot )
        
        self.annot.setMapPosition( pointXY )
        setFrameDocument()
        self.annot.setVisible( True )

    def remove(self):
        if self.annot:
            self.annotationManager.removeAnnotation( self.annot )

    def isVisible(self):
        if self.annot is None:
            return False

        return self.annot.isVisible()

    def toggle(self):
        if not self.annot is None:
            self.annot.setVisible( not self.annot.isVisible() )
            return

        self._create()

    @pyqtSlot('QgsAnnotation*')
    def annotationAboutToBeRemoved(self, annot):
        if annot == self.annot:
            self.annot = None

    def _create(self):
        annot = QgsTextAnnotation()
        opacity = 0.5
        dicSymbol = {
            'fill': {
                'create': QgsFillSymbol.createSimple,
                'setSymbol': annot.setFillSymbol,
                'properties': {
                    'color': 'white',
                    'width_border': '0.1',
                    'outline_color': 'gray', 'outline_style': 'solid'
                }
            },
            'marker': {
                'create': QgsMarkerSymbol.createSimple,
                'setSymbol': annot.setMarkerSymbol,
                'properties': { 'name': 'cross' }
            },
        }
        for k in dicSymbol:
            symbol = dicSymbol[ k ]['create']( dicSymbol[ k ]['properties'] )
            symbol.setOpacity( opacity )
            dicSymbol[ k ]['setSymbol']( symbol )

        self.annot = annot


class BaseEvent(QObject):
    def __init__(self, mapCanvas, crs, key_toggle, unitArea, unitLength):
        super().__init__()
        self.mapCanvas = mapCanvas
        self.key_toggle = key_toggle
        self.showAnotation = True # toggle by key_toggle
        self.unitArea, self.unitLength = unitArea, unitLength
        self.hasFilter = False
        self.annotationCanvas = AnnotationCanvas()
        self.project =  QgsProject.instance()
        self.measure = QgsDistanceArea()
        self.measure.setSourceCrs( crs, self.project.transformContext() )
        self.lastPoint = None

        self.objsToggleFilter = None # Need set by child class, Ex.:  ( mapCanvas, # Keyboard,  mapCanvas.viewport() # Mouse )

    def toggleFilter(self):
        def toggle(obj):
            f = obj.removeEventFilter if self.hasFilter else obj.installEventFilter
            f( self )

        for obj in self.objsToggleFilter:
            toggle( obj )

        self.hasFilter = not self.hasFilter

    def event_close(self):
        if self.hasFilter:
            self.toggleFilter()
        self.annotationCanvas.remove()

    def event_key_release_toggle(self):
        self.annotationCanvas.toggle()
        self.showAnotation = self.annotationCanvas.isVisible()

    def stringMeasures(self, data):
        def createString(length, area):
            value_ = round( self.measure.convertLengthMeasurement( length,  self.unitLength ), 2 )
            unit_ = QgsUnitTypes.toAbbreviatedString( self.unitLength )
            s_lenght = f"{value_} {unit_}"
            
            value_ = round( self.measure.convertAreaMeasurement( area,  self.unitArea ), 2 )
            unit_ = QgsUnitTypes.toAbbreviatedString( self.unitArea )
            s_area = f"{value_} {unit_}"

            return f"Area: {s_area}\nPerimeter: {s_lenght}" if s_area else f"Length: {s_lenght}"

        if not ( isinstance( data, list ) or isinstance( data, QgsGeometry ) ):
            raise TypeError(f"Type data '{str( type( data) )}' not implemeted")

        if not isinstance( self.unitArea, QgsUnitTypes.AreaUnit ):
            raise TypeError(f"Unit measure '{QgsUnitTypes.toAbbreviatedString( self.unitArea )}' not implemeted")
        if not isinstance( self.unitLength, QgsUnitTypes.DistanceUnit ):
            raise TypeError(f"Unit measure '{QgsUnitTypes.toAbbreviatedString( self.unitLength )}' not implemeted")

        if isinstance( data, list): # List of xyPoints
            length = self.measure.measureLine( data )
            area = self.measure.measurePolygon( data )
            return createString( length, area )
        
        #   Geometry
        length = data.length()
        area = data.area()
        return createString( length, area )

    @pyqtSlot(QObject, QEvent)
    def eventFilter(self, watched, event):
        pass # Virtual


class AddFeatureEvent(BaseEvent):
    def __init__(self, mapCanvas, crs, key_toggle, unitArea, unitLength):
        super().__init__( mapCanvas, crs, key_toggle, unitArea, unitLength )
        self.objsToggleFilter = (
            mapCanvas, # Keyboard
            mapCanvas.viewport() # Mouse
        )
        self.points = []
    
    @pyqtSlot(QObject, QEvent)
    def eventFilter(self, watched, event):
        def xyCursor():
            x_ = event.localPos().x()
            y_ = event.localPos().y()
            return self.mapCanvas.getCoordinateTransform().toMapCoordinates( x_, y_)

        def showMeasure(xyPoint):
            points =   self.points + [ self._transformPoint( xyPoint ) ]
            label = self.stringMeasures( points )
            self.annotationCanvas.setText( label, xyPoint )

        def event_close():
            self.event_close() # Base class
            self.points.clear()

        def event_mouse_move():
            if len( self.points ) < 2:
                return

            self.lastPoint = xyCursor()
            if len( self.points ) > 2 and not self.annotationCanvas.isVisible():
                return

            if self.showAnotation:
                showMeasure( self.lastPoint )

        def event_mouse_release():
            def leftPress():
                self.points.append( self._transformPoint( xyCursor() ) )

            def rightPress():
                self._cleanAnnotation()

            btn = event.button()
            d = {
                Qt.LeftButton: leftPress,
                Qt.RightButton: rightPress
            }
            if btn in d:
                d[ btn ]()

        def event_key_release():
            def toggle():
                self.event_key_release_toggle()
                if self.showAnotation and len( self.points ) > 2:
                    showMeasure( self.lastPoint )

            def escape():
                self._cleanAnnotation()

            k = event.key()
            d = {
                Qt.Key_T: toggle,
                Qt.Key_Escape: escape
            }
            if k in d:
                d[ k ]()

        e_type = event.type()
        d = {
            QEvent.Close: event_close,
            QEvent.MouseMove: event_mouse_move,
            QEvent.MouseButtonRelease: event_mouse_release,
            QEvent.KeyRelease: event_key_release
        }
        if e_type in d:
            d[ e_type ]()
        
        return False

    def _transformPoint(self, pointXY):
        ct = QgsCoordinateTransform( self.project.crs(), self.measure.sourceCrs(), self.project )
        return ct.transform( pointXY )

    def _cleanAnnotation(self):
        self.annotationCanvas.remove()
        self.points.clear()


class ChangeGeometryEvent(BaseEvent):
    def __init__(self,  mapCanvas, crs, key_toggle, unitArea, unitLength):
        super().__init__( mapCanvas, crs, key_toggle, unitArea, unitLength )
        self.objsToggleFilter = (
            mapCanvas, # Keyboard
        )
        self.lastMessage = None
        self.hasConnect = False
        self.layer = None

    def enable(self, layer):
        self.layer = layer
        self.hasConnect = True
        layer.geometryChanged.connect( self.geometryChanged )
        self.ct = QgsCoordinateTransform( layer.sourceCrs(), self.measure.sourceCrs(), self.project )
        if not self.hasFilter:
            self.toggleFilter()

    def disable(self):
        self.hasConnect = False
        self.layer.geometryChanged.disconnect( self.geometryChanged )
        self.annotationCanvas.remove()
        if self.hasFilter:
            self.toggleFilter()

    @pyqtSlot(QObject, QEvent)
    def eventFilter(self, watched, event):
        def event_key_release():
            def toggle():
                self.event_key_release_toggle()
                if self.showAnotation:
                    self.annotationCanvas.setText( self.lastMessage, self.lastPoint )

            if event.key() == Qt.Key_T:
                toggle()

        e_type = event.type()
        d = {
            QEvent.Close: self.event_close,
            QEvent.KeyRelease: event_key_release
        }
        if e_type in d:
            d[ e_type ]()
        
        return False

    @pyqtSlot('QgsFeatureId', QgsGeometry)
    def geometryChanged(self, fid, geometry):
        geometry.transform( self.ct )
        self.lastMessage = self.stringMeasures( geometry )
        self.lastPoint = self.mapCanvas.getCoordinateTransform().toMapCoordinates( self.mapCanvas.mouseLastXY() )

        if self.showAnotation:
            self.annotationCanvas.setText( self.lastMessage, self.lastPoint )


class CalcAreaEvent(QObject):
    def __init__(self, iface):
        super().__init__()
        self.mapCanvas = iface.mapCanvas()
        self.iface = iface
        self.addFeatureEvent = None
        self.changeGeometryEvent =  None
        self.hasEnable = False

    def __del__(self):
        self.iface.currentLayerChanged.disconnect( self.currentLayerChanged )

    def init(self, crs, unitArea, unitLength):
        args = {
            'mapCanvas': self.mapCanvas,
            'crs': crs,
            'key_toggle': Qt.Key_T,
            'unitArea': unitArea,
            'unitLength': unitLength
        }
        self.addFeatureEvent = AddFeatureEvent( **args )
        self.changeGeometryEvent = ChangeGeometryEvent( **args )
        self.mapCanvas.mapToolSet.connect( self.changeMapTool )
        self.iface.currentLayerChanged.connect( self.currentLayerChanged )
        self.hasEnable = True

        # Enable if current tool is Edit
        self.changeMapTool( self.mapCanvas.mapTool(), None )

    def disable(self):
        self.mapCanvas.mapToolSet.disconnect( self.changeMapTool )
        self.iface.currentLayerChanged.disconnect( self.currentLayerChanged )

        if self.addFeatureEvent.hasFilter:
            self.addFeatureEvent.toggleFilter()
        self.addFeatureEvent = None

        if self.changeGeometryEvent.hasConnect:
            self.changeGeometryEvent.disable()
        self.changeGeometryEvent =  None

        self.hasEnable = False

    @pyqtSlot(QgsMapTool, QgsMapTool)
    def changeMapTool(self, newTool, oldTool):
        def disableFeatures(disable_addFeatureEvent=True, disable_changeGeometry=True):
            if disable_addFeatureEvent and self.addFeatureEvent.hasFilter:
                self.addFeatureEvent.toggleFilter()
            if disable_changeGeometry and self.changeGeometryEvent.hasConnect:
                self.changeGeometryEvent.disable()

        mapTool = newTool
        if not isinstance( mapTool, QgsMapTool ):
            mapTool = self.mapCanvas.mapTool()

        if not isinstance( mapTool, QgsMapTool ):
            disableFeatures()
            return

        if not  mapTool.flags() == QgsMapTool.EditTool:
            disableFeatures()
            return

        if not self._isValidLayer( self.mapCanvas.currentLayer() ):
            disableFeatures()
            return

        name = mapTool.action().objectName()
        if not name == 'mActionAddFeature':
            disableFeatures( disable_changeGeometry=False )
            if not self.changeGeometryEvent.hasConnect:
                self.changeGeometryEvent.enable( self.mapCanvas.currentLayer() )
            return

        disableFeatures( disable_addFeatureEvent=False )
        if not self.addFeatureEvent.hasFilter:
            self.addFeatureEvent.toggleFilter()

    @pyqtSlot('QgsMapLayer*')
    def currentLayerChanged(self, layer):
        if self._isValidLayer( layer ) and self.changeGeometryEvent.hasConnect:
            self.changeGeometryEvent.disable()
            self.changeGeometryEvent.enable( layer )

    def _isValidLayer(self, layer):
        return \
            False if \
                layer is None or \
                not layer.type() == QgsMapLayerType.VectorLayer or \
                not layer.geometryType() == QgsWkbTypes.PolygonGeometry \
        else True
