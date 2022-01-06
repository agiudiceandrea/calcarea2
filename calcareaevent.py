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
            self.annot = None

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

    def stringMeasures(self, geometry):
        def createString(length, area):
            def getString(value, unit, f_measure):
                value_ = round( f_measure( value, unit  ), 2 )
                unit_ = QgsUnitTypes.toAbbreviatedString( unit )
                return f"{value_} {unit_}"

            s_lenght = getString( length, self.crs_unit['length'], self.measure.convertLengthMeasurement )
            s_area = getString( area, self.crs_unit['area'], self.measure.convertAreaMeasurement )

            return f"Area: {s_area}\nPerimeter: {s_lenght}"

        if not isinstance( self.crs_unit['area'], QgsUnitTypes.AreaUnit ):
            raise TypeError(f"Unit measure '{QgsUnitTypes.toAbbreviatedString( self.crs_unit['area'] )}' not implemeted")
        if not isinstance( self.crs_unit['length'], QgsUnitTypes.DistanceUnit ):
            raise TypeError(f"Unit measure '{QgsUnitTypes.toAbbreviatedString( self.crs_unit['length'] )}' not implemeted")

        length = geometry.length()
        area = geometry.area()
        return createString( length, area )

    @pyqtSlot()
    def crsChanged(self):
        self.ctProject2Measure.setSourceCrs( self.project.crs() )

    @pyqtSlot(QObject, QEvent)
    def eventFilter(self, watched, event):
        pass # Virtual


class AddFeatureEvent(BasePolygonEvent):
    def __init__(self, iface):
        mapCanvas = iface.mapCanvas()
        super().__init__( mapCanvas )
        self.objsToggleFilter = [
            mapCanvas, # Keyboard
            mapCanvas.viewport() # Mouse
        ]
        self.geomPolygon = self.GeomPolygon( iface )
        self.movePoint = None
        self.isValidLayer = False

    def __del__(self):
        super().__del__()
        del self.geomPolygon

    @pyqtSlot(QObject, QEvent)
    def eventFilter(self, watched, event):
        def xyCursor():
            x_ = event.localPos().x()
            y_ = event.localPos().y()
            return self.mapCanvas.getCoordinateTransform().toMapCoordinates( x_, y_)

        def showMeasure():
            geom = self.geomPolygon.geometry( self.ctProject2Measure.transform( self.movePoint ) )
            label = self.stringMeasures( geom )
            self.annotationCanvas.setText( label, self.movePoint )

        def event_mouse_move():
            if not self.isValidLayer or not self.isEnabled:
                return

            if self.geomPolygon.count() < 2:
                self.annotationCanvas.remove()
                return

            self.movePoint = xyCursor()
            showMeasure()

        def event_mouse_release():
            def leftPress():
                self.geomPolygon.add( self.ctProject2Measure.transform( xyCursor() ) )

            def rightPress():
                if self.isEnabled and self.geomPolygon.count() > 2:
                    if self.geomPolygon.isMiddlePoint():
                        self.geomPolygon.pop()
                    xyPoint = self.ctProject2Measure.transform( self.geomPolygon.coordinate(-1), QgsCoordinateTransform.ReverseTransform )
                    label = self.stringMeasures( self.geomPolygon.geometry() )
                    self.annotationCanvas.setText( label, xyPoint )
                self.geomPolygon.clear()

            if not self.isValidLayer:
                return

            k = event.button()
            d = {
                Qt.LeftButton: leftPress,
                Qt.RightButton: rightPress
            }
            if k in d:
                d[ k ]()

        def event_key_release():
            def key_escape():
                self.geomPolygon.clear()
                self.annotationCanvas.remove()

            def key_delete():
                if self.geomPolygon.count() > 1:
                    self.geomPolygon.pop(True)
                    self.annotationCanvas.remove()

            k = event.key()
            d = {
                Qt.Key_Escape: key_escape,
                Qt.Key_Delete: key_delete
            }
            if k in d:
                d[ k ]()

        e_type = event.type()
        d = {
            QEvent.MouseMove: event_mouse_move,
            QEvent.MouseButtonRelease: event_mouse_release,
            QEvent.KeyRelease: event_key_release
        }
        if e_type in d:
            d[ e_type ]()
        
        return False

    class GeomPolygon(QObject):
        def __init__(self, iface):
            def getActionDigitizeWithCurve(iface):
                name = 'advancedDigitizeToolBar'
                toolBar = getattr( iface, name, None)
                if toolBar is None:
                    raise TypeError(f"QgisInterface missing '{name}' toolbar")
                
                name = 'mActionDigitizeWithCurve'
                actions = [ action for action in iface.advancedDigitizeToolBar().actions() if action.objectName() == name ]
                if not len( actions ):
                    raise TypeError(f"QgisInterface missing '{name}' action")
                
                return actions[0]

            super().__init__()
            self.points = []
            self.idsMiddleCurve = []
            self.isCurve = False
            self.actionDigitizeWithCurve = getActionDigitizeWithCurve( iface )
            self.actionDigitizeWithCurve.toggled.connect( self.toggledCurve )

        def __del__(self):
            self.actionDigitizeWithCurve.toggled.disconnect( self.toggledCurve )

        def count(self):
            return len( self.points )

        def add(self, point):
            def populateIdCurves():
                idPoint = len( self.points ) -1
                if len( self.points) == 1: # Started curve
                    return

                totalIds = len( self.idsMiddleCurve )
                if not totalIds: # Added first middle point
                    self.idsMiddleCurve.append( idPoint )
                    return

                idPrev = self.idsMiddleCurve[ totalIds-1 ]
                if idPrev == idPoint-1: # Finished curve
                    return

                self.idsMiddleCurve.append( idPoint )

            self.points.append( point )
            if self.isCurve:
                populateIdCurves()

        def pop(self, key_delete=False):
            self.points.pop()
            if not key_delete and self.isCurve:
                self.idsMiddleCurve.pop()
                return

            if not len( self.idsMiddleCurve ):
                return

            # Check idPoint end of Curve
            idPoint = len( self.points ) - 1
            if idPoint == ( self.idsMiddleCurve[-1] ): # Middle
                self.points.pop() # Start
                self.idsMiddleCurve.pop()

        def coordinate(self, position):
            return self.points[ position ]

        def clear(self):
            self.points.clear()
            self.idsMiddleCurve.clear()

        def isMiddlePoint(self):
            return self.isCurve and len( self.idsMiddleCurve ) > 1 and self.idsMiddleCurve[-1] == ( len(self.points)-1 )

        def geometry(self, movePoint=None):
            def getCurvePolygon(points):
                def toPointString(id):
                    point = points[ id ] 
                    return point.toString(20).replace(',', ' ')

                idPoint = 0
                lenPoints = len( points )
                l_wkt = []
                while idPoint < lenPoints-1:
                    # Points
                    if not idPoint in self.idsMiddleCurve:
                        l_str = [ toPointString( idPoint ), toPointString( idPoint + 1 ) ]
                        if idPoint == ( lenPoints - 2 ):
                            l_str.append( toPointString(0) )
                        wkt = f"( {','.join( l_str )} )"
                        l_wkt.append( wkt )
                        idPoint += 1
                        continue
                    # CircularString
                    id = 0 if idPoint == 0 else idPoint - 1 # Test for first point
                    l_str = ( toPointString( id ), toPointString( id + 1 ), toPointString( id + 2 ) )
                    wkt = f"CircularString( {','.join( l_str )} )"
                    l_wkt.append( wkt )
                    # idCurve += 1
                    idPoint += 2

                if l_wkt[-1].find('CircularString') > -1:
                    l_str = [ toPointString( lenPoints-1 ), toPointString(0) ]
                    wkt = f"( {','.join( l_str )} )"
                    l_wkt.append( wkt )

                return QgsGeometry.fromWkt( f"CurvePolygon( CompoundCurve( {','.join( l_wkt )} ) )" )

            totalCurves = len( self.idsMiddleCurve )
            points = self.points if movePoint is None else self.points + [ movePoint ]
            if not totalCurves:
                return QgsGeometry.fromPolygonXY( [ points ] )

            return getCurvePolygon( points )

        @pyqtSlot(bool)
        def toggledCurve(self, checked):
            self.isCurve = checked


class ChangeGeometryEvent(BasePolygonEvent):
    def __init__(self,  mapCanvas):
        super().__init__( mapCanvas )
        self.objsToggleFilter = [ mapCanvas.viewport() ] # Mouse 
        self.layer = None # self.enable, self.changeLayer
        self.ctGeometry = None # self._configLayer
        self.project.layerWillBeRemoved.connect( self.layerWillBeRemoved )

    def __del__(self):
        super().__del__()
        self.project.layerWillBeRemoved.disconnect( self.layerWillBeRemoved )

    def enable(self):
        super().enable()
        self.layer = self.mapCanvas.currentLayer()
        self._configLayer()

    def disable(self):
        super().disable()
        if not self.layer is None:
            self.layer.geometryChanged.disconnect( self.geometryChanged )

    def changeLayer(self, layer):
        self.layer.geometryChanged.disconnect( self.geometryChanged )
        self.layer = layer
        self._configLayer()

    def eventFilter(self, watched, event):
        if event.type() == QEvent.MouseMove:
            self.annotationCanvas.remove()
        
        return False

    @pyqtSlot(str)
    def layerWillBeRemoved(self, layerId):
        if not self.layer is None and layerId == self.layer.id():
            self.layer.geometryChanged.disconnect( self.geometryChanged )
            self.layer = None

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
        self.addFeatureEvent = AddFeatureEvent( iface )
        self.changeGeometryEvent =  ChangeGeometryEvent( self.mapCanvas )
        self.currentEvent = None

        isValid = self._isValidLayer( self.mapCanvas.currentLayer() )
        self.addFeatureEvent.isValidLayer = isValid

        self.mapCanvas.mapToolSet.connect( self.changeMapTool )
        self.iface.currentLayerChanged.connect( self.currentLayerChanged )

    def __del__(self):
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
    def changeMapTool(self, newTool, oldTool=None):
        def enableEvent(event, enabled=True):
            # Enable: if not isEventFiltered
            # Disable: if isEventFiltered
            funcValid = ( lambda filter: not filter ) if enabled else ( lambda filter: filter )
            if funcValid( event.isEventFiltered ):
                event.toggleEventFilter()

        # Remove annotations
        for event in ( self.addFeatureEvent, self.changeGeometryEvent ):
            event.annotationCanvas.remove()

        self.currentEvent = None

        mapTool = newTool
        if not isinstance( mapTool, QgsMapTool ):
            mapTool = self.mapCanvas.mapTool()

        enableEvent( self.addFeatureEvent, False )
        enableEvent( self.changeGeometryEvent, False )
        if not isinstance( mapTool, QgsMapTool ) or \
           not mapTool.flags() == QgsMapTool.EditTool or \
           not self._isValidLayer( self.mapCanvas.currentLayer() ):
           return

        name = mapTool.action().objectName()
        self.currentEvent = self.addFeatureEvent if name == 'mActionAddFeature' else self.changeGeometryEvent
        enableEvent( self.currentEvent )

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
           not self.changeGeometryEvent.layer == layer:
           self.changeGeometryEvent.changeLayer( layer)
            
    def _isValidLayer(self, layer):
        return \
            False if \
                layer is None or \
                not layer.type() == QgsMapLayerType.VectorLayer or \
                not layer.geometryType() == QgsWkbTypes.PolygonGeometry \
        else True
