"""
Model exported as python.
Name : Catchment Analysis
Group : Hydrology
With QGIS : 33414
Created by Izza P.A. using QGIS Model Builder
"""

from qgis.core import QgsProcessing
from qgis.core import QgsProcessingAlgorithm
from qgis.core import QgsProcessingMultiStepFeedback
from qgis.core import QgsProcessingParameterVectorDestination
from qgis.core import QgsProcessingParameterFeatureSink
from qgis.core import QgsProcessingParameterRasterDestination
import processing


class CatchmentAnalysis(QgsProcessingAlgorithm):

    def initAlgorithm(self, config=None):
        self.addParameter(QgsProcessingParameterVectorDestination('CatchmentVector', 'Catchment (Vector)', type=QgsProcessing.TypeVectorPolygon, createByDefault=True, defaultValue=None))
        self.addParameter(QgsProcessingParameterFeatureSink('StreamNetworkInsideCatchment', 'Stream Network Inside Catchment', type=QgsProcessing.TypeVectorAnyGeometry, createByDefault=True, defaultValue=None))
        self.addParameter(QgsProcessingParameterRasterDestination('StreamThreshold', 'Stream (Threshold)', createByDefault=True, defaultValue=None))
        self.addParameter(QgsProcessingParameterVectorDestination('StreamVector', 'Stream (Vector)', type=QgsProcessing.TypeVectorLine, createByDefault=True, defaultValue=None))
        self.addParameter(QgsProcessingParameterRasterDestination('FilledDem', 'Filled DEM', createByDefault=True, defaultValue=None))
        self.addParameter(QgsProcessingParameterRasterDestination('StrahlerStream', 'Strahler Stream', createByDefault=True, defaultValue=None))
        self.addParameter(QgsProcessingParameterRasterDestination('CatchmentRaster', 'Catchment (Raster)', createByDefault=True, defaultValue=None))

    def processAlgorithm(self, parameters, context, model_feedback):
        # Use a multi-step feedback, so that individual child algorithm progress reports are adjusted for the
        # overall progress through the model
        feedback = QgsProcessingMultiStepFeedback(7, model_feedback)
        results = {}
        outputs = {}

        # Fill sinks (wang & liu)
        alg_params = {
            'ELEV': 'dem_3d878c95_7467_4658_89fc_f7e8119c33bc',
            'MINSLOPE': 0.001,
            'FDIR': QgsProcessing.TEMPORARY_OUTPUT,
            'FILLED': parameters['FilledDem'],
            'WSHED': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['FillSinksWangLiu'] = processing.run('sagang:fillsinkswangliu', alg_params, context=context, feedback=feedback, is_child_algorithm=True)
        results['FilledDem'] = outputs['FillSinksWangLiu']['FILLED']

        feedback.setCurrentStep(1)
        if feedback.isCanceled():
            return {}

        # Strahler order
        alg_params = {
            'DEM': outputs['FillSinksWangLiu']['FILLED'],
            'STRAHLER': parameters['StrahlerStream']
        }
        outputs['StrahlerOrder'] = processing.run('sagang:strahlerorder', alg_params, context=context, feedback=feedback, is_child_algorithm=True)
        results['StrahlerStream'] = outputs['StrahlerOrder']['STRAHLER']

        feedback.setCurrentStep(2)
        if feedback.isCanceled():
            return {}

        # Upslope area
        alg_params = {
            'CONVERGE': 1.1,
            'ELEVATION': outputs['FillSinksWangLiu']['FILLED'],
            'METHOD': 0,  # [0] Deterministic 8
            'MFD_CONTOUR': False,
            'SINKROUTE': None,
            'TARGET': None,
            'TARGET_PT_X': 558563.99,
            'TARGET_PT_Y': 55011.783,
            'AREA': parameters['CatchmentRaster']
        }
        outputs['UpslopeArea'] = processing.run('sagang:upslopearea', alg_params, context=context, feedback=feedback, is_child_algorithm=True)
        results['CatchmentRaster'] = outputs['UpslopeArea']['AREA']

        feedback.setCurrentStep(3)
        if feedback.isCanceled():
            return {}

        # Polygonize (raster to vector)
        alg_params = {
            'BAND': 1,
            'EIGHT_CONNECTEDNESS': False,
            'EXTRA': '',
            'FIELD': 'DN',
            'INPUT': outputs['UpslopeArea']['AREA'],
            'OUTPUT': parameters['CatchmentVector']
        }
        outputs['PolygonizeRasterToVector'] = processing.run('gdal:polygonize', alg_params, context=context, feedback=feedback, is_child_algorithm=True)
        results['CatchmentVector'] = outputs['PolygonizeRasterToVector']['OUTPUT']

        feedback.setCurrentStep(4)
        if feedback.isCanceled():
            return {}

        # Raster calculator
        alg_params = {
            'CELL_SIZE': None,
            'CRS': None,
            'EXPRESSION': '"A@1" >= 7',
            'EXTENT': None,
            'LAYERS': outputs['StrahlerOrder']['STRAHLER'],
            'OUTPUT': parameters['StreamThreshold']
        }
        outputs['RasterCalculator'] = processing.run('native:modelerrastercalc', alg_params, context=context, feedback=feedback, is_child_algorithm=True)
        results['StreamThreshold'] = outputs['RasterCalculator']['OUTPUT']

        feedback.setCurrentStep(5)
        if feedback.isCanceled():
            return {}

        # Channel network and drainage basins
        alg_params = {
            'DEM': outputs['FillSinksWangLiu']['FILLED'],
            'SUBBASINS': False,
            'THRESHOLD': 7,
            'BASINS': QgsProcessing.TEMPORARY_OUTPUT,
            'SEGMENTS': parameters['StreamVector']
        }
        outputs['ChannelNetworkAndDrainageBasins'] = processing.run('sagang:channelnetworkanddrainagebasins', alg_params, context=context, feedback=feedback, is_child_algorithm=True)
        results['StreamVector'] = outputs['ChannelNetworkAndDrainageBasins']['SEGMENTS']

        feedback.setCurrentStep(6)
        if feedback.isCanceled():
            return {}

        # Clip
        alg_params = {
            'INPUT': outputs['ChannelNetworkAndDrainageBasins']['SEGMENTS'],
            'OVERLAY': outputs['PolygonizeRasterToVector']['OUTPUT'],
            'OUTPUT': parameters['StreamNetworkInsideCatchment']
        }
        outputs['Clip'] = processing.run('native:clip', alg_params, context=context, feedback=feedback, is_child_algorithm=True)
        results['StreamNetworkInsideCatchment'] = outputs['Clip']['OUTPUT']
        return results

    def name(self):
        return 'Catchment Analysis'

    def displayName(self):
        return 'Catchment Analysis'

    def group(self):
        return 'Hydrology'

    def groupId(self):
        return ''

    def createInstance(self):
        return CatchmentAnalysis()
