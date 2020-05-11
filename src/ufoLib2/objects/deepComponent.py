import warnings
from typing import TYPE_CHECKING, Optional, Tuple

import attr
from fontTools.misc.transform import Identity, Transform
from fontTools.pens.basePen import AbstractPen
from fontTools.pens.pointPen import AbstractPointPen, PointToSegmentPen

from ufoLib2.objects.misc import BoundingBox

from .misc import _convert_transform, getBounds, getControlBounds

if TYPE_CHECKING:
    from ufoLib2.objects.layer import Layer


@attr.s(auto_attribs=True, slots=True)
class DeepComponent:
    """Represents a reference to another glyph that has several layer or glyph variations.
    """

    baseGlyph: str
    """The name of the glyph in the same layer to insert."""

    transformation: list # x, y, scalex, scaley, rotate

    coord: list

    identifier: Optional[str] = None
    """The globally unique identifier of the component."""

    # def move(self, delta: Tuple[float, float]) -> None:
    #     """Moves this component by (x, y) font units."""
    #     x, y = delta
    #     self.transformation = self.transformation.translate(x, y)

    # def getBounds(self, layer: "Layer") -> Optional[BoundingBox]:
    #     """Returns the (xMin, yMin, xMax, yMax) bounding box of the component,
    #     taking the actual contours into account.

    #     Args:
    #         layer: The layer of the containing glyph to look up components.
    #     """
    #     return getBounds(self, layer)

    # def getControlBounds(self, layer: "Layer") -> Optional[BoundingBox]:
    #     """Returns the (xMin, yMin, xMax, yMax) bounding box of the component,
    #     taking only the control points into account.

    #     Gives inaccurate results with extruding curvatures.

    #     Args:
    #         layer: The layer of the containing glyph to look up components.
    #     """
    #     return getControlBounds(self, layer)

    # -----------
    # Pen methods
    # -----------

    def draw(self, pen: AbstractPen) -> None:
        """Draws component with given pen."""
        pointPen = PointToSegmentPen(pen)
        self.drawPoints(pointPen)

    def drawPoints(self, pointPen: AbstractPointPen) -> None:
        """Draws points of deep component with given point pen."""
        try:
            pointPen.addDeepComponent(
                self.baseGlyph, self.transformation, self.coord, identifier=self.identifier
            )
        except TypeError:
            pointPen.addDeepComponent(self.baseGlyph, self.transformation, self.coord)
            warnings.warn(
                "The addDeepComponent method needs an identifier kwarg. "
                "The component's identifier value has been discarded.",
                UserWarning,
            )
