import os
import shutil
import fs.tempfs
from ufoLib2.constants import DEFAULT_LAYER_NAME
from ufoLib2.objects.dataSet import DataSet
from ufoLib2.objects.guideline import Guideline
from ufoLib2.objects.imageSet import ImageSet
from ufoLib2.objects.info import Info
from ufoLib2.objects.layerSet import LayerSet
from ufoLib2.objects.features import Features
from fontTools.misc.py23 import basestring
from fontTools.ufoLib import UFOReader, UFOWriter, UFOFileStructure


class Font(object):
    _fields = (
        "layers",
        "info",
        "features",
        "groups",
        "kerning",
        "lib",
        "data",
        "images",
    )
    __slots__ = _fields + ("_path", "_reader", "_fileStructure")

    def __init__(
        self,
        layers=None,
        info=None,
        features=None,
        groups=None,
        kerning=None,
        lib=None,
        data=None,
        images=None,
    ):
        self.layers = LayerSet() if layers is None else layers
        self.info = (
            info
            if isinstance(info, Info)
            else Info(**info)
            if info is not None
            else Info()
        )
        self.features = (
            features
            if isinstance(features, Features)
            else Features(features or "")
        )
        self.groups = {} if groups is None else groups
        self.kerning = {} if kerning is None else kerning
        self.lib = {} if lib is None else lib
        self.data = (
            data
            if isinstance(data, DataSet)
            else DataSet(**data)
            if data is not None
            else DataSet()
        )
        self.images = (
            images
            if isinstance(images, ImageSet)
            else ImageSet(**images)
            if images is not None
            else ImageSet()
        )

        self._path = None
        self._reader = None
        self._fileStructure = None

    @classmethod
    def open(cls, path, lazy=True, validate=True):
        reader = UFOReader(path, validate=validate)
        self = cls.read(reader, lazy=lazy)
        self._path = path
        self._fileStructure = reader.fileStructure
        if lazy:
            # keep the reader around so we can close it when done
            self._reader = reader
        else:
            reader.close()
        return self

    @classmethod
    def read(cls, reader, lazy=True):
        layers = LayerSet.read(reader, lazy=lazy)
        data = DataSet.read(reader, lazy=lazy)
        images = ImageSet.read(reader, lazy=lazy)
        info = Info()
        reader.readInfo(info)
        features = Features(reader.readFeatures())
        groups = reader.readGroups()
        kerning = reader.readKerning()
        lib = reader.readLib()
        self = cls(
            layers=layers,
            info=info,
            features=features,
            groups=groups,
            kerning=kerning,
            lib=lib,
            data=data,
            images=images,
        )
        return self

    def __contains__(self, name):
        return name in self.layers.defaultLayer

    def __delitem__(self, name):
        del self.layers.defaultLayer[name]

    def __getitem__(self, name):
        return self.layers.defaultLayer[name]

    def __setitem__(self, name, glyph):
        self.layers.defaultLayer[name] = glyph

    def __iter__(self):
        return iter(self.layers.defaultLayer)

    def __len__(self):
        return len(self.layers.defaultLayer)

    def get(self, name, default=None):
        return self.layers.defaultLayer.get(name, default)

    def keys(self):
        return self.layers.defaultLayer.keys()

    def close(self):
        if self._reader is not None:
            self._reader.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, exc_tb):
        self.close()

    def __repr__(self):
        names = list(filter(None, [self.info.familyName, self.info.styleName]))
        fontName = " '{}'".format(" ".join(names)) if names else ""
        return "<{}.{}{} at {}>".format(
            self.__class__.__module__,
            self.__class__.__name__,
            fontName,
            hex(id(self)),
        )

    @property
    def reader(self):
        return self._reader

    @property
    def glyphOrder(self):
        return list(self.lib.get("public.glyphOrder", []))

    @glyphOrder.setter
    def glyphOrder(self, value):
        if value is None or len(value) == 0:
            value = 0
            if "public.glyphOrder" in self.lib:
                del self.lib["public.glyphOrder"]
        else:
            self.lib["public.glyphOrder"] = value

    @property
    def guidelines(self):
        return self.info.guidelines

    @guidelines.setter
    def guidelines(self, value):
        for guideline in value:
            self.appendGuideline(guideline)

    @property
    def path(self):
        try:
            return self._path
        except AttributeError:
            return

    def addGlyph(self, glyph):
        self.layers.defaultLayer.addGlyph(glyph)

    def newGlyph(self, name):
        return self.layers.defaultLayer.newGlyph(name)

    def newLayer(self, name, **kwargs):
        return self.layers.newLayer(name, **kwargs)

    def renameGlyph(self, name, newName, overwrite=False):
        self.layers.defaultLayer.renameGlyph(name, newName, overwrite)

    def renameLayer(self, name, newName, overwrite=False):
        self.layers.renameLayer(name, newName, overwrite)

    def appendGuideline(self, guideline):
        if not isinstance(guideline, Guideline):
            guideline = Guideline(**guideline)
        self.info.guidelines.append(guideline)

    def write(self, writer, saveAs=None):
        if saveAs is None:
            saveAs = self._reader is not writer
        # TODO move this check to fontTools UFOWriter
        if self.layers.defaultLayer.name != DEFAULT_LAYER_NAME:
            assert DEFAULT_LAYER_NAME not in self.layers.layerOrder
        # save font attrs
        writer.writeFeatures(self.features.text)
        writer.writeGroups(self.groups)
        writer.writeInfo(self.info)
        writer.writeKerning(self.kerning)
        writer.writeLib(self.lib)
        # save the layers
        self.layers.write(writer, saveAs=saveAs)
        # save bin parts
        self.data.write(writer, saveAs=saveAs)
        self.images.write(writer, saveAs=saveAs)

    def save(
        self,
        path=None,
        formatVersion=3,
        structure=None,
        overwrite=False,
        validate=True,
    ):
        if formatVersion != 3:
            raise NotImplementedError(
                "unsupported format version: %s" % formatVersion
            )
        # validate 'structure' argument
        if structure is not None:
            structure = UFOFileStructure(structure)
        elif self._fileStructure is not None:
            # if structure is None, fall back to the same as when first loaded
            structure = self._fileStructure

        if hasattr(path, "__fspath__"):
            path = path.__fspath__()
        if isinstance(path, basestring):
            path = os.path.normpath(path)
        # else we assume it's an fs.BaseFS and we pass it on to UFOWriter

        overwritePath = tmp = None

        saveAs = path is not None
        if saveAs:
            if isinstance(path, basestring) and os.path.exists(path):
                if overwrite:
                    overwritePath = path
                    tmp = fs.tempfs.TempFS()
                    path = tmp.getsyspath(os.path.basename(path))
                else:
                    import errno

                    raise OSError(
                        errno.EEXIST, "path %r already exists" % path
                    )
        elif self.path is None:
            raise TypeError("'path' is required when saving a new Font")
        else:
            path = self.path

        try:
            with UFOWriter(
                path, structure=structure, validate=validate
            ) as writer:
                self.write(writer, saveAs=saveAs)
            writer.setModificationTime()
        except Exception:
            raise
        else:
            if overwritePath is not None:
                # remove existing then move file to destination
                if os.path.isdir(overwritePath):
                    shutil.rmtree(overwritePath)
                elif os.path.isfile(overwritePath):
                    os.remove(overwritePath)
                shutil.move(path, overwritePath)
                path = overwritePath
        finally:
            # clean up the temporary directory
            if tmp is not None:
                tmp.close()

        self._path = path
