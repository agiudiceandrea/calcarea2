# -*- coding: utf-8 -*-
"""
/***************************************************************************
Name                 : Calc Area 2.
Description          : Show layer area and length when editing
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
    pyqtSlot, pyqtSignal
)
from qgis.PyQt.QtGui import QFont, QTextDocument

from qgis.core import (
    QgsGeometry,
    QgsMapLayerType, QgsWkbTypes,
    QgsDistanceArea,
    QgsUnitTypes,
    QgsCoordinateReferenceSystem, QgsCoordinateTransform,
    QgsProject,
    QgsTextAnnotation, QgsMarkerSymbol, QgsFillSymbol,
)
from qgis.gui import QgsMapTool


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


class BasePolygonEvent(QObject):
    def __init__(self, mapCanvas):
        super().__init__()
        self.mapCanvas = mapCanvas
        self.crs_unit = {
            'crs': QgsCoordinateReferenceSystem('EPSG:3857'),
            'area': QgsUnitTypes.AreaHectares,
            'length': QgsUnitTypes.DistanceMeters
        }
        self.annotationCanvas = AnnotationCanvas()
        self.project =  QgsProject.instance()
        self.project.crsChanged.connect( self.crsChanged )
        self.measure = QgsDistanceArea()
        self.measure.setSourceCrs( self.crs_unit['crs'], self.project.transformContext() )
        self.ctProject2Measure = QgsCoordinateTransform( self.project.crs(), self.crs_unit['crs'], self.project )
        self.isEnabled = False # Annotation
        self.isEventFiltered = False

        self.objsToggleFilter = None # Need set by child class, Ex.:  ( mapCanvas, # Keyboard,  mapCanvas.viewport() # Mouse )

    def __del__(self):
        self.project.crsChanged.disconnect( self.crsChanged )

    def setCrsUnit(self, crs_unit):
        for k in self.crs_unit:
            self.crs_unit[ k ] = crs_unit[ k ]
        self.measure.setSourceCrs( self.crs_unit['crs'], self.project.transformContext() )
        self.ctProject2Measure.setDestinationCrs( self.crs_unit['crs'] )

    def enable(self):
        self.isEnabled = True

    def disable(self):
        self.annotationCanvas.remove()
        self.isEnabled = False

    def toggleEventFilter(self):
        def toggle(obj):
            f = obj.removeEventFilter if self.isEventFiltered else obj.installEventFilter
            f( self )

        if self.objsToggleFilter is None:
            return

        for obj in self.objsToggleFilter:
            toggle( obj )

        self.isEventFiltered = not self.isEventFiltered

    def stringMeasures(self, data):
        def createString(length, area):
            def getString(value, unit, f_measure):
                value_ = round( f_measure( value, unit  ), 2 )
                unit_ = QgsUnitTypes.toAbbreviatedString( unit )
                return f"{value_} {unit_}"

            s_lenght = getString( length, self.crs_unit['length'], self.measure.convertLengthMeasurement )
            s_area = getString( area, self.crs_unit['area'], self.measure.convertAreaMeasurement )

            return f"Area: {s_area}\nPerimeter: {s_lenght}"

        if not ( isinstance( data, list ) or isinstance( data, QgsGeometry ) ):
            raise TypeError(f"Type data '{str( type( data ) )}' not implemeted")
        if not isinstance( self.crs_unit['area'], QgsUnitTypes.AreaUnit ):
            raise TypeError(f"Unit measure '{QgsUnitTypes.toAbbreviatedString( self.crs_unit['area'] )}' not implemeted")
        if not isinstance( self.crs_unit['length'], QgsUnitTypes.DistanceUnit ):
            raise TypeError(f"Unit measure '{QgsUnitTypes.toAbbreviatedString( self.crs_unit['length'] )}' not implemeted")

        if isinstance( data, list): # List of xyPoints
            length = self.measure.measureLine( data )
            area = self.measure.measurePolygon( data )
            return createString( length, area )
        
        #   Geometry
        length = data.length()
        area = data.area()
        return createString( length, area )

    @pyqtSlot()
    def crsChanged(self):
        self.ctProject2Measure.setSourceCrs( self.project.crs() )


    @pyqtSlot(QObject, QEvent)
    def eventFilter(self, watched, event):
        pass # Virtual


class AddFeatureEvent(BasePolygonEvent):
    def __init__(self, mapCanvas):
        super().__init__( mapCanvas )
        self.objsToggleFilter = (
            mapCanvas, # Keyboard
            mapCanvas.viewport() # Mouse
        )
        self.points = []
        self.movePoint = None
        self.isValidLayer = False
    
    @pyqtSlot(QObject, QEvent)
    def eventFilter(self, watched, event):
        def xyCursor():
            x_ = event.localPos().x()
            y_ = event.localPos().y()
            return self.mapCanvas.getCoordinateTransform().toMapCoordinates( x_, y_)

        def showMeasure():
            label = self.stringMeasures( self.points + [ self.ctProject2Measure.transform( self.movePoint ) ] )
            self.annotationCanvas.setText( label, self.movePoint )

        def event_mouse_move():
            if not self.isValidLayer or not self.isEnabled:
                return

            if len( self.points ) < 2:
                return

            self.movePoint = xyCursor()
            showMeasure()

        def event_mouse_release():
            def leftPress():
                self.points.append( self.ctProject2Measure.transform( xyCursor() ) )

            def rightPress():
                if self.isEnabled and \
                    len ( self.points ): # Twice clicked
                    xyPoint = self.ctProject2Measure.transform( self.points[-1],  QgsCoordinateTransform.ReverseTransform )
                    label = self.stringMeasures( self.points )
                    self.annotationCanvas.setText( label, xyPoint )
                self.points.clear()

            if not self.isValidLayer:
                return

            btn = event.button()
            d = {
                Qt.LeftButton: leftPress,
                Qt.RightButton: rightPress
            }
            if btn in d:
                d[ btn ]()

        def event_key_release():
            if event.key() == Qt.Key_Escape:
                self.points.clear()

        e_type = event.type()
        d = {
            QEvent.MouseMove: event_mouse_move,
            QEvent.MouseButtonRelease: event_mouse_release,
            QEvent.KeyRelease: event_key_release
        }
        if e_type in d:
            d[ e_type ]()
        
        return False


class ChangeGeometryEvent(BasePolygonEvent):
    def __init__(self,  mapCanvas):
        super().__init__( mapCanvas )
        # Not event filter: self.objsToggleFilter = None and self.isFiltered = False (Base class)
        self.layer = None # self.enable, self.changeLayer
        self.ctGeometry = None # self._configLayer

    def enable(self):
        super().enable()
        self.layer = self.mapCanvas.currentLayer()
        self._configLayer()

    def disable(self):
        super().disable()
        self.layer.geometryChanged.disconnect( self.geometryChanged )

    def changeLayer(self, layer):
        self.layer.geometryChanged.disconnect( self.geometryChanged )
        self.layer = layer
        self._configLayer()

    @pyqtSlot('QgsFeatureId', QgsGeometry)
    def geometryChanged(self, fid, geometry):
        if not self.isEnabled:
            return

        geometry.transform( self.ctGeometry )
        msg = self.stringMeasures( geometry )
        pointXY = self.mapCanvas.getCoordinateTransform().toMapCoordinates( self.mapCanvas.mouseLastXY() )
        self.annotationCanvas.setText( msg, pointXY )

    def _configLayer(self):
        self.layer.geometryChanged.connect( self.geometryChanged )
        self.ctGeometry = QgsCoordinateTransform( self.layer.sourceCrs(), self.measure.sourceCrs(), self.project )


class CalcAreaEvent(QObject):
    validLayer = pyqtSignal(bool)
    def __init__(self, iface):
        super().__init__()
        self.iface = iface
        self.mapCanvas = iface.mapCanvas()
        self.addFeatureEvent = AddFeatureEvent( self.mapCanvas )
        self.changeGeometryEvent =  ChangeGeometryEvent( self.mapCanvas )
        self.currentEvent = None

        isValid = self._isValidLayer( self.mapCanvas.currentLayer() )
        self.addFeatureEvent.isValidLayer = isValid

        self.mapCanvas.mapToolSet.connect( self.changeMapTool )
        self.iface.currentLayerChanged.connect( self.currentLayerChanged )

    def __del__(self):
        super().__del__()

        if self.addFeatureEvent.isEnabled:
            self.addFeatureEvent.disable()
        if self.addFeatureEvent.isEventFiltered:
            self.addFeatureEvent.toggleEventFilter()

        if self.changeGeometryEvent.isEnabled:
            self.changeGeometryEvent.disable()

        self.mapCanvas.mapToolSet.disconnect( self.changeMapTool )
        self.iface.currentLayerChanged.disconnect( self.currentLayerChanged )

    def run(self, checked):
        def enable(events):
            for event in events:
                if not event.isEnabled:
                    event.enable()

        def disable(events):
            for event in events:
                if event.isEnabled:
                    event.disable()

        events = ( self.addFeatureEvent, self.changeGeometryEvent )
        enable( events ) if checked else disable( events )

    def setCrsUnit(self, crs_unit):
        self.addFeatureEvent.setCrsUnit( crs_unit )
        self.changeGeometryEvent.setCrsUnit( crs_unit )

    def getCrsUnit(self):
        return self.addFeatureEvent.crs_unit

    @pyqtSlot(QgsMapTool, QgsMapTool)
    def changeMapTool(self, newTool, oldTool):
        def disableFeatures(status):
            if status['addFeatureEvent']:
                if self.addFeatureEvent.isEventFiltered:
                    self.addFeatureEvent.toggleEventFilter()
                if self.addFeatureEvent.isEnabled:
                    self.addFeatureEvent.annotationCanvas.remove()

            if status['changeGeometry'] and self.changeGeometryEvent.isEnabled:
                self.changeGeometryEvent.disable()

        self.currentEvent = None

        mapTool = newTool
        if not isinstance( mapTool, QgsMapTool ):
            mapTool = self.mapCanvas.mapTool()

        status = {
            'addFeatureEvent': True,
            'changeGeometry': True
        }
        if not isinstance( mapTool, QgsMapTool ):
            disableFeatures( status )
            return

        if not mapTool.flags() == QgsMapTool.EditTool:
            disableFeatures( status )
            return

        if not self._isValidLayer( self.mapCanvas.currentLayer() ):
            disableFeatures( status )
            return

        name = mapTool.action().objectName()
        if not name == 'mActionAddFeature':
            status['changeGeometry'] = False
            disableFeatures( status )
            self.currentEvent = self.changeGeometryEvent
            if not self.changeGeometryEvent.isEnabled:
                self.changeGeometryEvent.enable()
            return

        status['addFeatureEvent'] = False
        disableFeatures( status )
        self.currentEvent = self.addFeatureEvent
        if not self.addFeatureEvent.isEventFiltered:
            self.addFeatureEvent.toggleEventFilter()

    @pyqtSlot('QgsMapLayer*')
    def currentLayerChanged(self, layer):
        isValid = self._isValidLayer( layer )
        self.validLayer.emit( isValid )
        self.addFeatureEvent.isValidLayer = isValid

        if not isValid and not self.currentEvent is None:
            self.currentEvent.annotationCanvas.remove()

        if isValid and \
        self.currentEvent == self.changeGeometryEvent and \
        self.changeGeometryEvent.isEnabled and \
        not self.changeGeometryEvent == layer:
           self.changeGeometryEvent.changeLayer( layer)
            
    def _isValidLayer(self, layer):
        return \
            False if \
                layer is None or \
                not layer.type() == QgsMapLayerType.VectorLayer or \
                not layer.geometryType() == QgsWkbTypes.PolygonGeometry \
        else True
