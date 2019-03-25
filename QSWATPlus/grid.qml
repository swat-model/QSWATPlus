<!DOCTYPE qgis PUBLIC 'http://mrcc.com/qgis.dtd' 'SYSTEM'>
<qgis simplifyMaxScale="1" hasScaleBasedVisibilityFlag="0" simplifyDrawingTol="1" maxScale="0" minScale="1e+08" styleCategories="AllStyleCategories" labelsEnabled="1" version="3.4.5-Madeira" simplifyDrawingHints="1" simplifyAlgorithm="0" readOnly="0" simplifyLocal="1">
  <flags>
    <Identifiable>1</Identifiable>
    <Removable>1</Removable>
    <Searchable>1</Searchable>
  </flags>
  <renderer-v2 symbollevels="0" enableorderby="0" type="RuleRenderer" forceraster="0">
    <rules key="{a91f1344-fc60-4b87-8637-ce265fab9cf3}">
      <rule filter="&quot;LakeId&quot; IS NULL AND &quot;Subbasin&quot; > 0" label="nonlake" key="{67c77a71-e0ec-49d0-9684-1f64c24f9b13}" symbol="0"/>
      <rule filter="&quot;LakeId&quot; IS NOT NULL" label="lake" key="{cf51ac01-3597-4219-975d-809b6090c781}" symbol="1"/>
      <rule filter=" &quot;LakeId&quot;  IS NULL AND  &quot;Subbasin&quot;  IS NULL" label="empty" key="{182d8450-1473-4c6b-9b8d-4df53d770572}" symbol="2"/>
    </rules>
    <symbols>
      <symbol name="0" type="fill" clip_to_extent="1" force_rhr="0" alpha="1">
        <layer class="SimpleFill" pass="0" locked="0" enabled="1">
          <prop k="border_width_map_unit_scale" v="3x:0,0,0,0,0,0"/>
          <prop k="color" v="109,248,204,0"/>
          <prop k="joinstyle" v="bevel"/>
          <prop k="offset" v="0,0"/>
          <prop k="offset_map_unit_scale" v="3x:0,0,0,0,0,0"/>
          <prop k="offset_unit" v="MM"/>
          <prop k="outline_color" v="0,0,0,255"/>
          <prop k="outline_style" v="solid"/>
          <prop k="outline_width" v="0.26"/>
          <prop k="outline_width_unit" v="MM"/>
          <prop k="style" v="no"/>
          <data_defined_properties>
            <Option type="Map">
              <Option name="name" type="QString" value=""/>
              <Option name="properties"/>
              <Option name="type" type="QString" value="collection"/>
            </Option>
          </data_defined_properties>
        </layer>
      </symbol>
      <symbol name="1" type="fill" clip_to_extent="1" force_rhr="0" alpha="1">
        <layer class="SimpleFill" pass="0" locked="0" enabled="1">
          <prop k="border_width_map_unit_scale" v="3x:0,0,0,0,0,0"/>
          <prop k="color" v="27,252,255,255"/>
          <prop k="joinstyle" v="bevel"/>
          <prop k="offset" v="0,0"/>
          <prop k="offset_map_unit_scale" v="3x:0,0,0,0,0,0"/>
          <prop k="offset_unit" v="MM"/>
          <prop k="outline_color" v="35,35,35,255"/>
          <prop k="outline_style" v="solid"/>
          <prop k="outline_width" v="0.26"/>
          <prop k="outline_width_unit" v="MM"/>
          <prop k="style" v="solid"/>
          <data_defined_properties>
            <Option type="Map">
              <Option name="name" type="QString" value=""/>
              <Option name="properties"/>
              <Option name="type" type="QString" value="collection"/>
            </Option>
          </data_defined_properties>
        </layer>
      </symbol>
      <symbol name="2" type="fill" clip_to_extent="1" force_rhr="0" alpha="1">
        <layer class="SimpleFill" pass="0" locked="0" enabled="1">
          <prop k="border_width_map_unit_scale" v="3x:0,0,0,0,0,0"/>
          <prop k="color" v="145,82,45,255"/>
          <prop k="joinstyle" v="bevel"/>
          <prop k="offset" v="0,0"/>
          <prop k="offset_map_unit_scale" v="3x:0,0,0,0,0,0"/>
          <prop k="offset_unit" v="MM"/>
          <prop k="outline_color" v="35,35,35,255"/>
          <prop k="outline_style" v="no"/>
          <prop k="outline_width" v="0.26"/>
          <prop k="outline_width_unit" v="MM"/>
          <prop k="style" v="no"/>
          <data_defined_properties>
            <Option type="Map">
              <Option name="name" type="QString" value=""/>
              <Option name="properties"/>
              <Option name="type" type="QString" value="collection"/>
            </Option>
          </data_defined_properties>
        </layer>
      </symbol>
    </symbols>
  </renderer-v2>
  <labeling type="simple">
    <settings>
      <text-style fontCapitals="0" fontWordSpacing="0" fontFamily="MS Shell Dlg 2" fieldName="CASE WHEN &quot;Subbasin&quot; = 0 OR &quot;LakeId&quot; THEN '' ELSE &quot;Subbasin&quot; END" textOpacity="1" useSubstitutions="0" previewBkgrdColor="#ffffff" textColor="0,0,0,255" multilineHeight="1" fontStrikeout="0" fontSizeUnit="Point" isExpression="1" fontWeight="50" fontLetterSpacing="0" fontUnderline="0" namedStyle="Regular" fontSizeMapUnitScale="3x:0,0,0,0,0,0" fontSize="8.25" fontItalic="0" blendMode="0">
        <text-buffer bufferColor="255,255,255,255" bufferSizeMapUnitScale="3x:0,0,0,0,0,0" bufferBlendMode="0" bufferDraw="0" bufferSize="1" bufferSizeUnits="MM" bufferJoinStyle="128" bufferOpacity="1" bufferNoFill="0"/>
        <background shapeRotation="0" shapeRotationType="0" shapeFillColor="255,255,255,255" shapeBlendMode="0" shapeRadiiY="0" shapeSizeY="0" shapeBorderWidth="0" shapeDraw="0" shapeSizeUnit="MM" shapeBorderColor="128,128,128,255" shapeType="0" shapeRadiiX="0" shapeRadiiMapUnitScale="3x:0,0,0,0,0,0" shapeRadiiUnit="MM" shapeOffsetUnit="MM" shapeSVGFile="" shapeSizeX="0" shapeOffsetX="0" shapeOffsetY="0" shapeOffsetMapUnitScale="3x:0,0,0,0,0,0" shapeBorderWidthUnit="MM" shapeSizeMapUnitScale="3x:0,0,0,0,0,0" shapeSizeType="0" shapeBorderWidthMapUnitScale="3x:0,0,0,0,0,0" shapeJoinStyle="64" shapeOpacity="1"/>
        <shadow shadowDraw="0" shadowBlendMode="6" shadowOffsetAngle="135" shadowUnder="0" shadowRadiusMapUnitScale="3x:0,0,0,0,0,0" shadowOffsetGlobal="1" shadowRadiusUnit="MM" shadowScale="100" shadowColor="0,0,0,255" shadowOpacity="0.7" shadowRadiusAlphaOnly="0" shadowOffsetMapUnitScale="3x:0,0,0,0,0,0" shadowOffsetUnit="MM" shadowRadius="1.5" shadowOffsetDist="1"/>
        <substitutions/>
      </text-style>
      <text-format leftDirectionSymbol="&lt;" wrapChar="" addDirectionSymbol="0" plussign="0" multilineAlign="4294967295" formatNumbers="0" placeDirectionSymbol="0" decimals="3" useMaxLineLengthForAutoWrap="1" autoWrapLength="0" reverseDirectionSymbol="0" rightDirectionSymbol=">"/>
      <placement offsetType="0" repeatDistanceUnits="MM" priority="5" repeatDistanceMapUnitScale="3x:0,0,0,0,0,0" centroidInside="0" rotationAngle="0" maxCurvedCharAngleIn="25" preserveRotation="1" labelOffsetMapUnitScale="3x:0,0,0,0,0,0" distUnits="MM" quadOffset="4" maxCurvedCharAngleOut="-25" dist="0" distMapUnitScale="3x:0,0,0,0,0,0" xOffset="0" repeatDistance="0" offsetUnits="MapUnit" placementFlags="10" fitInPolygonOnly="1" centroidWhole="0" placement="1" predefinedPositionOrder="TR,TL,BR,BL,R,L,TSR,BSR" yOffset="0"/>
      <rendering scaleVisibility="0" fontLimitPixelSize="0" displayAll="0" maxNumLabels="2000" upsidedownLabels="0" mergeLines="0" drawLabels="1" scaleMax="10000000" fontMinPixelSize="3" obstacle="1" fontMaxPixelSize="10000" labelPerPart="0" obstacleType="0" limitNumLabels="0" minFeatureSize="0" zIndex="0" obstacleFactor="1" scaleMin="1"/>
      <dd_properties>
        <Option type="Map">
          <Option name="name" type="QString" value=""/>
          <Option name="properties"/>
          <Option name="type" type="QString" value="collection"/>
        </Option>
      </dd_properties>
    </settings>
  </labeling>
  <customproperties>
    <property key="dualview/previewExpressions">
      <value>"PolygonId"</value>
    </property>
    <property key="embeddedWidgets/count" value="0"/>
    <property key="labeling/enabled" value="true"/>
    <property key="variableNames"/>
    <property key="variableValues"/>
  </customproperties>
  <blendMode>0</blendMode>
  <featureBlendMode>0</featureBlendMode>
  <layerOpacity>1</layerOpacity>
  <SingleCategoryDiagramRenderer attributeLegend="1" diagramType="Histogram">
    <DiagramCategory sizeType="MM" opacity="1" sizeScale="3x:0,0,0,0,0,0" width="15" penWidth="0" scaleBasedVisibility="0" height="15" penAlpha="255" lineSizeScale="3x:0,0,0,0,0,0" lineSizeType="MM" enabled="0" diagramOrientation="Up" minScaleDenominator="0" minimumSize="0" barWidth="5" rotationOffset="270" penColor="#000000" maxScaleDenominator="1e+08" scaleDependency="Area" labelPlacementMethod="XHeight" backgroundAlpha="255" backgroundColor="#ffffff">
      <fontProperties style="" description="MS Shell Dlg 2,8.25,-1,5,50,0,0,0,0,0"/>
      <attribute field="" label="" color="#000000"/>
    </DiagramCategory>
  </SingleCategoryDiagramRenderer>
  <DiagramLayerSettings showAll="1" placement="0" dist="0" linePlacementFlags="2" priority="0" zIndex="0" obstacle="0">
    <properties>
      <Option type="Map">
        <Option name="name" type="QString" value=""/>
        <Option name="properties"/>
        <Option name="type" type="QString" value="collection"/>
      </Option>
    </properties>
  </DiagramLayerSettings>
  <geometryOptions geometryPrecision="0" removeDuplicateNodes="0">
    <activeChecks/>
    <checkConfiguration/>
  </geometryOptions>
  <fieldConfiguration>
    <field name="PolygonId">
      <editWidget type="TextEdit">
        <config>
          <Option/>
        </config>
      </editWidget>
    </field>
    <field name="DownId">
      <editWidget type="TextEdit">
        <config>
          <Option/>
        </config>
      </editWidget>
    </field>
    <field name="Area">
      <editWidget type="TextEdit">
        <config>
          <Option/>
        </config>
      </editWidget>
    </field>
    <field name="Subbasin">
      <editWidget type="TextEdit">
        <config>
          <Option/>
        </config>
      </editWidget>
    </field>
    <field name="LakeId">
      <editWidget type="TextEdit">
        <config>
          <Option/>
        </config>
      </editWidget>
    </field>
  </fieldConfiguration>
  <aliases>
    <alias field="PolygonId" name="" index="0"/>
    <alias field="DownId" name="" index="1"/>
    <alias field="Area" name="" index="2"/>
    <alias field="Subbasin" name="" index="3"/>
    <alias field="LakeId" name="" index="4"/>
  </aliases>
  <excludeAttributesWMS/>
  <excludeAttributesWFS/>
  <defaults>
    <default field="PolygonId" applyOnUpdate="0" expression=""/>
    <default field="DownId" applyOnUpdate="0" expression=""/>
    <default field="Area" applyOnUpdate="0" expression=""/>
    <default field="Subbasin" applyOnUpdate="0" expression=""/>
    <default field="LakeId" applyOnUpdate="0" expression=""/>
  </defaults>
  <constraints>
    <constraint field="PolygonId" exp_strength="0" notnull_strength="0" constraints="0" unique_strength="0"/>
    <constraint field="DownId" exp_strength="0" notnull_strength="0" constraints="0" unique_strength="0"/>
    <constraint field="Area" exp_strength="0" notnull_strength="0" constraints="0" unique_strength="0"/>
    <constraint field="Subbasin" exp_strength="0" notnull_strength="0" constraints="0" unique_strength="0"/>
    <constraint field="LakeId" exp_strength="0" notnull_strength="0" constraints="0" unique_strength="0"/>
  </constraints>
  <constraintExpressions>
    <constraint field="PolygonId" exp="" desc=""/>
    <constraint field="DownId" exp="" desc=""/>
    <constraint field="Area" exp="" desc=""/>
    <constraint field="Subbasin" exp="" desc=""/>
    <constraint field="LakeId" exp="" desc=""/>
  </constraintExpressions>
  <expressionfields/>
  <attributeactions>
    <defaultAction key="Canvas" value="{00000000-0000-0000-0000-000000000000}"/>
  </attributeactions>
  <attributetableconfig sortExpression="&quot;PolygonId&quot;" actionWidgetStyle="dropDown" sortOrder="0">
    <columns>
      <column name="PolygonId" type="field" width="-1" hidden="0"/>
      <column name="DownId" type="field" width="-1" hidden="0"/>
      <column name="Area" type="field" width="-1" hidden="0"/>
      <column name="Subbasin" type="field" width="-1" hidden="0"/>
      <column type="actions" width="-1" hidden="1"/>
      <column name="LakeId" type="field" width="-1" hidden="0"/>
    </columns>
  </attributetableconfig>
  <conditionalstyles>
    <rowstyles/>
    <fieldstyles/>
  </conditionalstyles>
  <editform tolerant="1">C:/PROGRA~1/QGIS3~1.4/bin</editform>
  <editforminit/>
  <editforminitcodesource>0</editforminitcodesource>
  <editforminitfilepath>C:/PROGRA~1/QGIS3~1.4/bin</editforminitfilepath>
  <editforminitcode><![CDATA[# -*- coding: utf-8 -*-
"""
QGIS forms can have a Python function that is called when the form is
opened.

Use this function to add extra logic to your forms.

Enter the name of the function in the "Python Init function"
field.
An example follows:
"""
from qgis.PyQt.QtWidgets import QWidget

def my_form_open(dialog, layer, feature):
	geom = feature.geometry()
	control = dialog.findChild(QWidget, "MyLineEdit")
]]></editforminitcode>
  <featformsuppress>0</featformsuppress>
  <editorlayout>generatedlayout</editorlayout>
  <editable>
    <field name="Area" editable="1"/>
    <field name="DownId" editable="1"/>
    <field name="LakeId" editable="1"/>
    <field name="PolygonId" editable="1"/>
    <field name="Subbasin" editable="1"/>
  </editable>
  <labelOnTop>
    <field labelOnTop="0" name="Area"/>
    <field labelOnTop="0" name="DownId"/>
    <field labelOnTop="0" name="LakeId"/>
    <field labelOnTop="0" name="PolygonId"/>
    <field labelOnTop="0" name="Subbasin"/>
  </labelOnTop>
  <widgets/>
  <previewExpression>PolygonId</previewExpression>
  <mapTip></mapTip>
  <layerGeometryType>2</layerGeometryType>
</qgis>
