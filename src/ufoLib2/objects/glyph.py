from copy import deepcopy
from typing import (
    TYPE_CHECKING,
    Any,
    Dict,
    Iterator,
    List,
    Mapping,
    Optional,
    Tuple,
    Union,
)

import attr
from fontTools.misc.transform import Transform
from fontTools.pens.basePen import AbstractPen
from fontTools.pens.pointPen import (
    AbstractPointPen,
    PointToSegmentPen,
    SegmentToPointPen,
)

from ufoLib2.objects.anchor import Anchor
from ufoLib2.objects.component import Component
from ufoLib2.objects.deepComponent import DeepComponent
from ufoLib2.objects.contour import Contour
from ufoLib2.objects.guideline import Guideline
from ufoLib2.objects.image import Image
from ufoLib2.objects.misc import BoundingBox, getBounds, getControlBounds
from ufoLib2.pointPens.glyphPointPen import GlyphPointPen

if TYPE_CHECKING:
    from ufoLib2.objects.layer import Layer  # noqa: F401

aegv_key = 'robocjk.atomicElement.glyphVariations'
dcae_key = 'robocjk.deepComponent.atomicElements'
cgdc_key = 'robocjk.characterGlyph.deepComponents'

@attr.s(auto_attribs=True, slots=True, repr=False)
class Glyph:
    """Represents a glyph, containing contours, components, anchors and various
    other bits of data concerning it.

    See http://unifiedfontobject.org/versions/ufo3/glyphs/glif/.

    Behavior:
        The Glyph object has list-like behavior. This behavior allows you to interact
        with contour data directly. For example, to get a particular contour::

            contour = glyph[0]

        To iterate over all contours::

            for contour in glyph:
                ...

        To get the number of contours::

            contourCount = len(glyph)

        To check if a :class:`.Contour` object is in glyph::

            exists = contour in glyph

        To interact with components or anchors in a similar way, use the
        :attr:`.Glyph.components` and :attr:`.Glyph.anchors` attributes.
    """

    _name: Optional[str] = None

    width: float = 0
    """The width of the glyph."""

    height: float = 0
    """The height of the glyph."""

    unicodes: List[int] = attr.ib(factory=list)
    """The Unicode code points assigned to the glyph. Note that a glyph can have
    multiple."""

    _image: Image = attr.ib(factory=Image)

    lib: Dict[str, Any] = attr.ib(factory=dict)
    """The glyph's mapping of string keys to arbitrary data."""

    note: Optional[str] = None
    """A free form text note about the glyph."""

    _anchors: List[Anchor] = attr.ib(factory=list)
    components: List[Component] = attr.ib(factory=list)
    """The list of components the glyph contains."""

    deepComponents: List[DeepComponent] = attr.ib(factory=list)

    glyphVariationLayers: List[str] = attr.ib(factory=list)

    variationGlyphs: List = attr.ib(factory=dict)

    contours: List[Contour] = attr.ib(factory=list)
    """The list of contours the glyph contains."""

    _guidelines: List[Guideline] = attr.ib(factory=list)

    def __len__(self) -> int:
        return len(self.contours)

    def __getitem__(self, index: int) -> Contour:
        return self.contours[index]

    def __contains__(self, contour: Contour) -> bool:
        return contour in self.contours

    def __iter__(self) -> Iterator[Contour]:
        return iter(self.contours)

    def __repr__(self) -> str:
        return "<{}.{} {}at {}>".format(
            self.__class__.__module__,
            self.__class__.__name__,
            f"'{self._name}' " if self._name is not None else "",
            hex(id(self)),
        )

    @property
    def anchors(self) -> List[Anchor]:
        """The list of anchors the glyph contains.

        Getter:
            Returns a list of anchors the glyph contains. Modifications of the list
            modify the Glyph object.

        Setter:
            Clears current anchors and sets the new ones.
        """
        return self._anchors

    @anchors.setter
    def anchors(self, value: List[Anchor]) -> None:
        self.clearAnchors()
        for anchor in value:
            self.appendAnchor(anchor)

    @property
    def guidelines(self) -> List[Guideline]:
        """The list of guidelines the glyph contains.

        Getter:
            Returns a list of guidelines the glyph contains. Modifications of the list
            modify the Glyph object.

        Setter:
            Clears current guidelines and sets the new ones.
        """
        return self._guidelines

    @guidelines.setter
    def guidelines(self, value: List[Guideline]) -> None:
        self.clearGuidelines()
        for guideline in value:
            self.appendGuideline(guideline)

    @property
    def name(self) -> Optional[str]:
        """The name of the glyph."""
        return self._name

    @property
    def unicode(self) -> Optional[int]:
        """The first assigned Unicode code point or None.

        See http://unifiedfontobject.org/versions/ufo3/glyphs/glif/#unicode.

        Setter:
            Sets the value to be the first of the assigned Unicode code points. Will
            remove a duplicate if exists. Will clear the list of Unicode points if
            value is None.
        """
        if self.unicodes:
            return self.unicodes[0]
        return None

    @unicode.setter
    def unicode(self, value: Optional[int]) -> None:
        if value is None:
            self.unicodes = []
        else:
            if self.unicodes:
                if self.unicodes[0] == value:
                    return
                try:
                    self.unicodes.remove(value)
                except ValueError:
                    pass
                self.unicodes.insert(0, value)
            else:
                self.unicodes.append(value)

    @property
    def image(self) -> Image:
        """The background image reference associated with the glyph.

        See http://unifiedfontobject.org/versions/ufo3/glyphs/glif/#image.

        Setter:
            Sets the background image reference. Clears it if value is None.
        """
        return self._image

    @image.setter
    def image(self, image: Optional[Union[Image, Mapping[str, Any]]]) -> None:
        if image is None:
            self._image.clear()
        elif isinstance(image, Image):
            self._image = image
        else:
            self._image = Image(
                fileName=image["fileName"],
                transformation=Transform(
                    image["xScale"],
                    image["xyScale"],
                    image["yxScale"],
                    image["yScale"],
                    image["xOffset"],
                    image["yOffset"],
                ),
                color=image.get("color"),
            )

    def clear(self) -> None:
        """Clears out anchors, components, contours, guidelines and image
        references."""
        del self._anchors[:]
        del self.components[:]
        del self.deepComponents[:]
        del self.contours[:]
        del self._guidelines[:]
        self.image.clear()

    def clearAnchors(self) -> None:
        """Clears out anchors."""
        del self._anchors[:]

    def clearContours(self) -> None:
        """Clears out contours."""
        del self.contours[:]

    def clearComponents(self) -> None:
        """Clears out components."""
        del self.components[:]

    def clearGuidelines(self) -> None:
        """Clears out guidelines."""
        del self._guidelines[:]

    def removeComponent(self, component: Component) -> None:
        """Removes :class:`.Component` object from the glyph's list of components."""
        self.components.remove(component)

    def appendAnchor(self, anchor: Union[Anchor, Mapping[str, Any]]) -> None:
        """Appends an :class:`.Anchor` object to glyph's list of anchors.

        Args:
            anchor: An :class:`.Anchor` object or mapping for the Anchor constructor.
        """
        if not isinstance(anchor, Anchor):
            if not isinstance(anchor, Mapping):
                raise TypeError(
                    "Expected Anchor object or a Mapping for the ",
                    f"Anchor constructor, found {type(anchor).__name__}",
                )
            anchor = Anchor(**anchor)
        self.anchors.append(anchor)

    def appendGuideline(self, guideline: Union[Guideline, Mapping[str, Any]]) -> None:
        """Appends a :class:`.Guideline` object to glyph's list of guidelines.

        Args:
            guideline: A :class:`.Guideline` object or a mapping for the Guideline
                constructor.
        """
        if not isinstance(guideline, Guideline):
            if not isinstance(guideline, Mapping):
                raise TypeError(
                    "Expected Guideline object or a Mapping for the ",
                    f"Guideline constructor, found {type(guideline).__name__}",
                )
            guideline = Guideline(**guideline)
        self._guidelines.append(guideline)

    def appendContour(self, contour: Contour) -> None:
        """Appends a :class:`.Contour` object to glyph's list of contours."""
        if not isinstance(contour, Contour):
            raise TypeError(f"Expected Contour, found {type(contour).__name__}",)
        self.contours.append(contour)

    def copy(self, name: Optional[str] = None) -> "Glyph":
        """Returns a new Glyph (deep) copy, optionally override the new glyph
        name."""
        other = deepcopy(self)
        if name is not None:
            other._name = name
        return other

    def copyDataFromGlyph(self, glyph: "Glyph") -> None:
        """Deep-copies everything from the other glyph into self, except for
        the name.

        Existing glyph data is overwritten.

        |defcon_compat|
        """
        self.width = glyph.width
        self.height = glyph.height
        self.unicodes = list(glyph.unicodes)
        self.image = deepcopy(glyph.image)
        self.note = glyph.note
        self.lib = deepcopy(glyph.lib)
        self.anchors = deepcopy(glyph.anchors)
        self.guidelines = deepcopy(glyph.guidelines)
        # NOTE: defcon's copyDataFromGlyph appends instead of overwrites here,
        # but we do the right thing, for consistency with the rest.
        self.clearContours()
        self.clearComponents()
        pointPen = self.getPointPen()
        glyph.drawPoints(pointPen)

    def move(self, delta: Tuple[float, float]) -> None:
        """Moves all contours, components and anchors by (x, y) font units."""
        for contour in self.contours:
            contour.move(delta)
        for component in self.components:
            component.move(delta)
        for anchor in self.anchors:
            anchor.move(delta)

    # -----------
    # Pen methods
    # -----------

    def draw(self, pen: AbstractPen) -> None:
        """Draws glyph into given pen."""
        # TODO: Document pen interface more or link to somewhere.
        pointPen = PointToSegmentPen(pen)
        self.drawPoints(pointPen)

    def drawPoints(self, pointPen: AbstractPointPen) -> None:
        """Draws points of glyph into given point pen."""
        for contour in self.contours:
            contour.drawPoints(pointPen)
        for component in self.components:
            component.drawPoints(pointPen)

        for e in [dcae_key, cgdc_key]:
            if e in self.lib:
                for dc in self.lib[e]:
                    transformation = [dc['x'], dc['y'], dc['scalex'], dc['scaley'], dc['rotation']]
                    # Note: coord attribute should be a list of tuples not a dict
                    # RoboCJK needs updating
                    coord = [[i, v] for i, (k, v) in enumerate(dc['coord'].items())]
                    dc = DeepComponent(dc['name'], transformation, coord)
                    dc.drawPoints(pointPen)
        
        if aegv_key in self.lib:
            glyphVariationLayers = [layerName for (axisName, layerName) in self.lib[aegv_key].items()]
            self.addDepth(glyphVariationLayers)
            if self.variationGlyphs:
                print('glyph HAS variations', len(self.variationGlyphs))


    def addDepth(self, glyphVariationLayers: list):
        self.glyphVariationLayers = glyphVariationLayers

    def addGlyphVariations(self, variationGlyphs: list):
        self.variationGlyphs = variationGlyphs

    def getPen(self) -> AbstractPen:
        """Returns a pen for others to draw into self."""
        pen = SegmentToPointPen(self.getPointPen())
        return pen

    def getPointPen(self) -> AbstractPointPen:
        """Returns a point pen for others to draw points into self."""
        pointPen = GlyphPointPen(self)
        return pointPen

    # lib wrapped attributes

    @property
    def markColor(self) -> Optional[str]:
        """The color assigned to the glyph.

        See http://unifiedfontobject.org/versions/ufo3/glyphs/glif/#publicmarkcolor.

        Getter:
            Returns the mark color or None.

        Setter:
            Sets the mark color. If value is None, deletes the key from the lib if
            present.
        """
        return self.lib.get("public.markColor")

    @markColor.setter
    def markColor(self, value: Optional[str]) -> None:
        if value is not None:
            self.lib["public.markColor"] = value
        elif "public.markColor" in self.lib:
            del self.lib["public.markColor"]

    @property
    def verticalOrigin(self) -> Optional[float]:
        """The vertical origin of the glyph.

        See http://unifiedfontobject.org/versions/ufo3/glyphs/glif/#publicverticalorigin.

        Getter:
            Returns the vertical origin or None.

        Setter:
            Sets the vertical origin. If value is None, deletes the key from the lib if
            present.
        """
        return self.lib.get("public.verticalOrigin")

    @verticalOrigin.setter
    def verticalOrigin(self, value: Optional[float]) -> None:
        if value is not None:
            self.lib["public.verticalOrigin"] = value
        elif "public.verticalOrigin" in self.lib:
            del self.lib["public.verticalOrigin"]

    # bounds and side-bearings

    def getBounds(self, layer: Optional["Layer"] = None) -> Optional[BoundingBox]:
        """Returns the (xMin, yMin, xMax, yMax) bounding box of the glyph,
        taking the actual contours into account.

        Args:
            layer: The layer of the glyph to look up components, if any. Not needed for
                pure-contour glyphs.
        """
        if layer is None and self.components:
            raise TypeError("layer is required to compute bounds of components")

        return getBounds(self, layer)

    def getControlBounds(
        self, layer: Optional["Layer"] = None
    ) -> Optional[BoundingBox]:
        """Returns the (xMin, yMin, xMax, yMax) bounding box of the glyph,
        taking only the control points into account.

        Gives inaccurate results with extruding curvatures.

        Args:
            layer: The layer of the glyph to look up components, if any. Not needed for
                pure-contour glyphs.
        """
        if layer is None and self.components:
            raise TypeError("layer is required to compute bounds of components")

        return getControlBounds(self, layer)

    def getLeftMargin(self, layer: Optional["Layer"] = None) -> Optional[float]:
        """Returns the the space in font units from the point of origin to the
        left side of the glyph.

        Args:
            layer: The layer of the glyph to look up components, if any. Not needed for
                pure-contour glyphs.
        """
        bounds = self.getBounds(layer)
        if bounds is None:
            return None
        return bounds.xMin

    def setLeftMargin(self, value: float, layer: Optional["Layer"] = None) -> None:
        """Sets the the space in font units from the point of origin to the
        left side of the glyph.

        Args:
            value: The desired left margin in font units.
            layer: The layer of the glyph to look up components, if any. Not needed for
                pure-contour glyphs.
        """
        bounds = self.getBounds(layer)
        if bounds is None:
            return None
        diff = value - bounds.xMin
        if diff:
            self.width += diff
            self.move((diff, 0))

    def getRightMargin(self, layer: Optional["Layer"] = None) -> Optional[float]:
        """Returns the the space in font units from the glyph's advance width
        to the right side of the glyph.

        Args:
            layer: The layer of the glyph to look up components, if any. Not needed for
                pure-contour glyphs.
        """
        bounds = self.getBounds(layer)
        if bounds is None:
            return None
        return self.width - bounds.xMax

    def setRightMargin(self, value: float, layer: Optional["Layer"] = None) -> None:
        """Sets the the space in font units from the glyph's advance width to
        the right side of the glyph.

        Args:
            value: The desired right margin in font units.
            layer: The layer of the glyph to look up components, if any. Not needed for
                pure-contour glyphs.
        """
        bounds = self.getBounds(layer)
        if bounds is None:
            return None
        self.width = bounds.xMax + value

    def getBottomMargin(self, layer: Optional["Layer"] = None) -> Optional[float]:
        """Returns the the space in font units from the bottom of the canvas to
        the bottom of the glyph.

        Args:
            layer: The layer of the glyph to look up components, if any. Not needed for
                pure-contour glyphs.
        """
        bounds = self.getBounds(layer)
        if bounds is None:
            return None
        if self.verticalOrigin is None:
            return bounds.yMin
        else:
            return bounds.yMin - (self.verticalOrigin - self.height)

    def setBottomMargin(self, value: float, layer: Optional["Layer"] = None) -> None:
        """Sets the the space in font units from the bottom of the canvas to
        the bottom of the glyph.

        Args:
            value: The desired bottom margin in font units.
            layer: The layer of the glyph to look up components, if any. Not needed for
                pure-contour glyphs.
        """
        bounds = self.getBounds(layer)
        if bounds is None:
            return None
        # blindly copied from defcon Glyph._set_bottomMargin; not sure it's correct
        if self.verticalOrigin is None:
            oldValue = bounds.yMin
            self.verticalOrigin = self.height
        else:
            oldValue = bounds.yMin - (self.verticalOrigin - self.height)
        diff = value - oldValue
        if diff:
            self.height += diff

    def getTopMargin(self, layer: Optional["Layer"] = None) -> Optional[float]:
        """Returns the the space in font units from the top of the canvas to
        the top of the glyph.

        Args:
            layer: The layer of the glyph to look up components, if any. Not needed for
                pure-contour glyphs.
        """
        bounds = self.getBounds(layer)
        if bounds is None:
            return None
        if self.verticalOrigin is None:
            return self.height - bounds.yMax
        else:
            return self.verticalOrigin - bounds.yMax

    def setTopMargin(self, value: float, layer: Optional["Layer"] = None) -> None:
        """Sets the the space in font units from the top of the canvas to the
        top of the glyph.

        Args:
            value: The desired top margin in font units.
            layer: The layer of the glyph to look up components, if any. Not needed for
                pure-contour glyphs.
        """
        bounds = self.getBounds(layer)
        if bounds is None:
            return
        if self.verticalOrigin is None:
            oldValue = self.height - bounds.yMax
        else:
            oldValue = self.verticalOrigin - bounds.yMax
        diff = value - oldValue
        if oldValue != value:
            # Is this still correct when verticalOrigin was not previously set?
            self.verticalOrigin = bounds.yMax + value
            self.height += diff
