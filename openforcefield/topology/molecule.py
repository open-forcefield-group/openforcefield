#!/usr/bin/env python

#=============================================================================================
# MODULE DOCSTRING
#=============================================================================================
"""
Molecular chemical entity representation and routines to interface with cheminformatics toolkits

.. todo::

   * Our main philosophy here is to keep the object contents of topology objects easily serializable/deserializable

   * Have ``Molecule`` raise an exception if loading/creating molecules with unspecified stereochemistry?
   * Create ``FrozenMolecule`` to represent immutable molecule
   * Make ``Atom`` and ``Bond`` an inner class of Molecule?
   * Add ``Molecule.from_smarts()`` or ``.from_tagged_smiles()`` to allow a tagged SMARTS string
     (where tags are zero-indexed atom indices) to be used to create a molecule with the given atom numbering.
   * How can we make the ``Molecule`` API more useful to codes like perses that modify molecules on the fly?
   * Use `attrs <http://www.attrs.org/>`_ for convenient class initialization?
   * JSON/BSON representations of objects?
   * Generalize Molecule infrastructure to provide "plug-in" support for cheminformatics toolkits
   * Do we need a way to write a bunch of molecules to a file, or serialize a set of molecules to a file?
     We currently don't have a way to do that through the ``Molecule`` API, even though there is a way to
     read multiple molecules via ``Molecules.from_file()``.
   * Should we allow the removal of atoms too?
   * Should invalidation of cached properties be handled via something like a tracked list?
   * Refactor toolkit encapsulation to generalize and provide only a few major toolkit methods and toolkit objects that can be queried for features
   * Speed up overall import time by putting non-global imports only where they are needed

"""

#=============================================================================================
# GLOBAL IMPORTS
#=============================================================================================

import numpy as np
from collections import OrderedDict, Counter
from copy import deepcopy
import operator

from simtk import unit
from simtk.openmm.app import element, Element

import networkx as nx
from networkx.algorithms.isomorphism import GraphMatcher

import openforcefield
from openforcefield.utils import serialize_numpy, deserialize_numpy, quantity_to_string, string_to_quantity
from openforcefield.utils.toolkits import ToolkitRegistry, ToolkitWrapper, RDKitToolkitWrapper, OpenEyeToolkitWrapper, \
    InvalidToolkitError, GLOBAL_TOOLKIT_REGISTRY
from openforcefield.utils.toolkits import DEFAULT_AROMATICITY_MODEL
from openforcefield.utils.serialization import Serializable


#=============================================================================================
# GLOBAL PARAMETERS
#=============================================================================================

# TODO: Can we have the `ALLOWED_*_MODELS` list automatically appear in the docstrings below?
# TODO: Should `ALLOWED_*_MODELS` be objects instead of strings?
# TODO: Should these be imported from `openforcefield.cheminformatics.aromaticity_models` and `.bondorder_models`?

# TODO: Allow all OpenEye aromaticity models to be used with OpenEye names?
#       Only support OEAroModel_MDL in RDKit version?

#=============================================================================================
# PRIVATE SUBROUTINES
#=============================================================================================

#=============================================================================================
# Particle
#=============================================================================================


class Particle(Serializable):
    """
    Base class for all particles in a molecule.

    A particle object could be an ``Atom`` or a ``VirtualSite``.

    .. warning :: This API is experimental and subject to change.
    """

    @property
    def molecule(self):
        """
        The ``Molecule`` this atom is part of.

        .. todo::

           * Should we have a single unique ``Molecule`` for each molecule type in the system,
           or if we have multiple copies of the same molecule, should we have multiple ``Molecule``s?
        """
        return self._molecule

    @molecule.setter
    def molecule(self, molecule):
        """
        Set the particle's molecule pointer. Note that this will only work if the particle currently
        doesn't have a molecule
        """
        #TODO: Add informative exception here
        assert self._molecule is None
        self._molecule = molecule

    @property
    def molecule_particle_index(self):
        """
        Returns the index of this particle in its molecule
        """
        return self._molecule.particles.index(self)

    @property
    def name(self):
        """
        The name of the particle
        """
        return self._name

    def to_dict(self):
        """Convert to dictionary representation."""
        # Implement abstract method Serializable.to_dict()
        raise NotImplementedError()  # TODO

    @classmethod
    def from_dict(cls, d):
        """Static constructor from dictionary representation."""
        # Implement abstract method Serializable.to_dict()
        raise NotImplementedError()  # TODO


#=============================================================================================
# Atom
#=============================================================================================


class Atom(Particle):
    """
    A particle representing a chemical atom.

    Note that non-chemical virtual sites are represented by the ``VirtualSite`` object.

    .. todo::

       * Should ``Atom`` objects be immutable or mutable?
       * Do we want to support the addition of arbitrary additional properties,
         such as floating point quantities (e.g. ``charge``), integral quantities (such as ``id`` or ``serial`` index in a PDB file),
         or string labels (such as Lennard-Jones types)?

    .. todo :: Allow atoms to have associated properties.

    .. warning :: This API is experimental and subject to change.
    """

    def __init__(self,
                 atomic_number,
                 formal_charge,
                 is_aromatic,
                 name=None,
                 molecule=None,
                 stereochemistry=None):
        """
        Create an immutable Atom object.

        Object is serializable and immutable.

        .. todo :: Use attrs to validate?

        .. todo :: We can add setters if we need to.

        Parameters
        ----------
        atomic_number : int
            Atomic number of the atom
        formal_charge : int
            Formal charge of the atom
        is_aromatic : bool
            If True, atom is aromatic; if False, not aromatic
        stereochemistry : str, optional, default=None
            Either 'R' or 'S' for specified stereochemistry, or None for ambiguous stereochemistry
        name : str, optional, default=None
            An optional name to be associated with the atom

        Examples
        --------

        Create a non-aromatic carbon atom

        >>> atom = Atom(6, 0, False)

        Create a chiral carbon atom

        >>> atom = Atom(6, 0, False, stereochemistry='R', name='CT')

        """
        self._atomic_number = atomic_number
        self._formal_charge = formal_charge
        self._is_aromatic = is_aromatic
        self._stereochemistry = stereochemistry
        if name is None:
            name = ''
        self._name = name
        self._molecule = molecule
        ## From Jeff: I'm going to assume that this is implicit in the parent Molecule's ordering of atoms
        #self._molecule_atom_index = molecule_atom_index
        self._bonds = list()
        self._virtual_sites = list()

    # TODO: We can probably avoid an explicit call and determine this dynamically
    #   from self._molecule (maybe caching the result) to get rid of some bookkeeping.
    def add_bond(self, bond):
        """Adds a bond that this atom is involved in
        .. todo :: Is this how we want to keep records?

        Parameters
        ----------
        bond: an openforcefield.topology.molecule.Bond
            A bond involving this atom

"""

        self._bonds.append(bond)
        #self._stereochemistry = None

    def add_virtual_site(self, vsite):
        """Adds a bond that this atom is involved in
        .. todo :: Is this how we want to keep records?

        Parameters
        ----------
        bond: an openforcefield.topology.molecule.Bond
            A bond involving this atom

"""

        self._virtual_sites.append(vsite)

    def to_dict(self):
        """Return a dict representation of the atom.

"""
        # TODO
        atom_dict = OrderedDict()
        atom_dict['atomic_number'] = self._atomic_number
        atom_dict['formal_charge'] = self._formal_charge
        atom_dict['is_aromatic'] = self._is_aromatic
        atom_dict['stereochemistry'] = self._stereochemistry
        # TODO: Should we let atoms have names?
        atom_dict['name'] = self._name
        # TODO: Should this be implicit in the atom ordering when saved?
        #atom_dict['molecule_atom_index'] = self._molecule_atom_index
        return atom_dict

    @classmethod
    def from_dict(cls, atom_dict):
        """Create an Atom from a dict representation.

"""
        ## TODO: classmethod or static method? Classmethod is needed for Bond, so it have
        ## its _molecule set and then look up the Atom on each side of it by ID
        return cls.__init__(*atom_dict)

    @property
    def formal_charge(self):
        """
        The atom's formal charge
        """
        return self._formal_charge

    @property
    def partial_charge(self):
        """
        The partial charge of the atom, if any.

        Returns
        -------
        simtk.unit.Quantity with dimension of atomic charge, or None if no charge has been specified
        """
        if self._molecule._partial_charges is None:
            return None
        else:
            index = self.molecule_atom_index
            return self._molecule._partial_charges[index]

    @property
    def is_aromatic(self):
        """
        The atom's is_aromatic flag
        """
        return self._is_aromatic

    @property
    def stereochemistry(self):
        """
        The atom's stereochemistry (if defined, otherwise None)
        """
        return self._stereochemistry

    @stereochemistry.setter
    def stereochemistry(self, value):
        """Set the atoms stereochemistry
        Parameters
        ----------
        value : str
            The stereochemistry around this atom, allowed values are "CW", "CCW", or None,
        """

        #if (value != 'CW') and (value != 'CCW') and not(value is None):
        #    raise Exception("Atom stereochemistry setter expected 'CW', 'CCW', or None. Received {} (type {})".format(value, type(value)))
        self._stereochemistry = value

    @property
    def element(self):
        """
        The element name

        """
        return element.Element.getByAtomicNumber(self._atomic_number)

    @property
    def atomic_number(self):
        """
        The integer atomic number of the atom.

        """
        return self._atomic_number

    @property
    def mass(self):
        """
        The standard atomic weight (abundance-weighted isotopic mass) of the atomic site.

        .. todo :: Should we discriminate between standard atomic weight and most abundant isotopic mass?
        TODO (from jeff): Are there atoms that have different chemical properties based on their isotopes?

        """
        return self.element.mass

    @property
    def name(self):
        """
        The name of this atom, if any
        """
        return self._name

    @name.setter
    def name(self, other):
        """

        Parameters
        ----------
        other : string
            The new name for this atom
        """
        if not (type(other) is str):
            raise Exception(
                "In setting atom name. Expected str, received {} (type {})".
                format(other, type(other)))
        self._name = other

    # TODO: How are we keeping track of bonds, angles, etc?

    @property
    def bonds(self):
        """
        The list of ``Bond`` objects this atom is involved in.

        """
        return self._bonds
        #for bond in self._bonds:
        #    yield bond

    @property
    #def bonded_to(self):
    def bonded_atoms(self):
        """
        The list of ``Atom`` objects this atom is involved in bonds with

        """
        for bond in self._bonds:
            for atom in bond.atoms:
                if not (atom == self):
                    # TODO: This seems dangerous. Ask John for a better way
                    yield atom

    def is_bonded_to(self, atom2):
        """
        Determine whether this atom is bound to another atom

        Parameters
        ----------
        atom2: openforcefield.topology.molecule.Atom
            a different atom in the same molecule

        Returns
        -------
        bool
            Whether this atom is bound to atom2
        """
        #TODO: Sanity check (check for same molecule?)
        assert self != atom2
        for bond in self._bonds:
            for bonded_atom in bond.atoms:
                if atom2 == bonded_atom:
                    return True
        return False

    @property
    def virtual_sites(self):
        """
        The list of ``VirtualSite`` objects this atom is involved in.

        """
        return self._virtual_sites
        #for vsite in self._vsites:
        #    yield vsite

    @property
    def molecule_atom_index(self):
        """
        The index of this Atom within the the list of atoms in ``Molecules``.
        Note that this can be different from ``molecule_particle_index``.

        """
        if self._molecule is None:
            raise ValueError('This Atom does not belong to a Molecule object')
        return self._molecule.atoms.index(self)

    @property
    def molecule_particle_index(self):
        """
        The index of this Atom within the the list of particles in the parent ``Molecule``.
        Note that this can be different from ``molecule_atom_index``.

        """
        if self._molecule is None:
            raise ValueError('This Atom does not belong to a Molecule object')
        return self._molecule.particles.index(self)

    # ## From Jeff: Not sure if we actually need this
    # @property
    # def topology_atom_index(self):
    #     """
    #     The index of this Atom within the the list of atoms in ``Topology``.
    #     Note that this can be different from ``particle_index``.
    #
    #     """
    #     if self._topology is None:
    #         raise ValueError('This Atom does not belong to a Topology object')
    #     # TODO: This will be slow; can we cache this and update it only when needed?
    #     #       Deleting atoms/molecules in the Topology would have to invalidate the cached index.
    #     return self._topology.atoms.index(self)

    def __repr__(self):
        # TODO: Also include particle_index and which molecule this atom belongs to?
        return "Atom(name={}, atomic number={})".format(
            self._name, self._atomic_number)

    def __str__(self):
        # TODO: Also include particle_index and which molecule this atom belongs to?
        return "<Atom name='{}' atomic number='{}'>".format(
            self._name, self._atomic_number)


#=============================================================================================
# VirtualSite
#=============================================================================================


class VirtualSite(Particle):
    """
    A particle representing a virtual site whose position is defined in terms of ``Atom`` positions.

    Note that chemical atoms are represented by the ``Atom``.


    .. warning :: This API is experimental and subject to change.

    .. todo::

       * Should a virtual site be able to belong to more than one Topology?
       * Should virtual sites be immutable or mutable?

    """

    def __init__(self,
                 atoms,
                 charge_increments=None,
                 epsilon=None,
                 sigma=None,
                 rmin_half=None,
                 name=None):
        """
        Base class for VirtualSites

        .. todo ::

           * This will need to be generalized for virtual sites to allow out-of-plane sites, which are not simply a linear combination of atomic positions
           * Add checking for allowed virtual site types
           * How do we want users to specify virtual site types?

        Parameters
        ----------
        atoms : list of Atom of shape [N]
            atoms[index] is the corresponding Atom for weights[index]
        charge_increments : list of floats of shape [N], optional, default=None
            The amount of charge to remove from the VirtualSite's atoms and put in the VirtualSite. Indexing in this list should match the ordering in the atoms list. Default is None.
        sigma : float, default=None
            Sigma term for VdW properties of virtual site. Default is None.
        epsilon : float
            Epsilon term for VdW properties of virtual site. Default is None.
        rmin_half : float
            Rmin_half term for VdW properties of virtual site. Default is None.
        name : string or None, default=None
            The name of this virtual site. Default is None.


        virtual_site_type : str
            Virtual site type.
        name : str or None, default=None
            The name of this virtual site. Default is None

"""

        # Ensure we have as many charge_increments as we do atoms
        if not (charge_increments is None):
            if not (len(charge_increments) == len(atoms)):
                raise Exception(
                    "VirtualSite definition must have same number of charge_increments ({}) and atoms({})"
                    .format(len(charge_increments), len(atoms)))

        # VdW parameters can either be epsilon+rmin_half or epsilon+sigma, but not both
        if not (epsilon is None):
            if ((rmin_half != None) and (sigma != None)):
                raise Exception(
                    "VirtualSite constructor given epsilon (value : {}), rmin_half (value : {}), and sigma (value : {}). If epsilon is nonzero, it should receive either rmin_half OR sigma"
                    .format(epsilon, rmin_half, sigma))
            if ((rmin_half is None) and (sigma is None)):
                raise Exception(
                    "VirtualSite constructor given epsilon (value : {}) but not given rmin_half (value : {}) or sigma (value : {})"
                    .format(epsilon, rmin_half, sigma))
            if (sigma is None):
                # TODO: Save the 6th root of 2 if this starts being slow.
                sigma = (2. * rmin_half) / (2.**(1. / 6))

        elif epsilon is None:
            if ((rmin_half != None) or (sigma != None)):
                raise Exception(
                    "VirtualSite constructor given rmin_half (value : {}) or sigma (value : {}), but not epsilon (value : {})"
                    .format(rmin_half, sigma, epsilon))

        # Perform type-checking
        for atom in atoms:
            assert isinstance(atom, Atom)
        for atom_index in range(len(atoms) - 1):
            assert atoms[atom_index].molecule is atoms[atom_index + 1].molecule
        assert isinstance(atoms[1].molecule, FrozenMolecule)

        if sigma is None:
            self._sigma = None
        else:
            assert hasattr(sigma, 'unit')
            assert unit.angstrom.is_compatible(sigma.unit)
            self._sigma = sigma.in_units_of(unit.angstrom)

        if epsilon is None:
            self._epsilon = None
        else:
            assert hasattr(epsilon, 'unit')
            assert (unit.kilojoule_per_mole).is_compatible(epsilon.unit)
            self._epsilon = epsilon.in_units_of(unit.kilojoule_per_mole)

        if charge_increments is None:
            self._charge_increments = None
        else:
            assert hasattr(charge_increments, 'unit')
            assert unit.elementary_charges.is_compatible(
                charge_increments.unit)
            self._charge_increments = charge_increments.in_units_of(
                unit.elementary_charges)

        self._atoms = list()
        for atom in atoms:
            atom.add_virtual_site(self)
            self._atoms.append(atom)
        self._molecule = atoms[0].molecule

        self._name = name

        # Subclassing makes _type unnecessary
        #self._type = None
        # TODO: Validate site types against allowed values

        #self._weights = np.array(weights) # make a copy and convert to array internally

    def to_dict(self):
        """Return a dict representation of the virtual site.

"""
        # Each subclass should have its own to_dict
        vsite_dict = OrderedDict()
        vsite_dict['name'] = self._name
        vsite_dict['atoms'] = tuple(
            [i.molecule_atom_index for i in self.atoms])
        vsite_dict['charge_increments'] = quantity_to_string(self._charge_increments)

        vsite_dict['epsilon'] = quantity_to_string(self._epsilon)

        vsite_dict['sigma'] = quantity_to_string(self._sigma)

        return vsite_dict

    @classmethod
    def from_dict(cls, vsite_dict):
        """Create a virtual site from a dict representation.

"""
        # Each subclass needs to have its own from_dict

        # Make a copy of the vsite_dict, where we'll unit-wrap the appropriate values
        vsite_dict_units = deepcopy(vsite_dict)

        # Attach units to epsilon term
        vsite_dict_units['epsilon'] = string_to_quantity(
            vsite_dict['epsilon'])
        vsite_dict_units['sigma'] = string_to_quantity(vsite_dict['sigma'])
        vsite_dict_units['charge_increments'] = string_to_quantity(
            vsite_dict['charge_increments'])

        return VirtualSite(**vsite_dict_units)

    @property
    def molecule_virtual_site_index(self):
        """
        The index of this VirtualSite within the list of virtual sites within ``Molecule``
        Note that this can be different from ``particle_index``.
        """
        #if self._topology is None:
        #    raise ValueError('This VirtualSite does not belong to a Topology object')
        # TODO: This will be slow; can we cache this and update it only when needed?
        #       Deleting atoms/molecules in the Topology would have to invalidate the cached index.
        return self._molecule.virtual_sites.index(self)

    @property
    def molecule_particle_index(self):
        """
        The index of this VirtualSite within the the list of particles in the parent ``Molecule``.
        Note that this can be different from ``molecule_virtual_site_index``.

        """
        if self._molecule is None:
            raise ValueError(
                'This VirtualSite does not belong to a Molecule object')
        return self._molecule.particles.index(self)

    @property
    def atoms(self):
        """
        Atoms on whose position this VirtualSite depends.
        """
        return self._atoms
        #for atom in self._atoms:
        #    yield atom

    @property
    def charge_increments(self):
        """
        Charges taken from this VirtualSite's atoms and given to the VirtualSite
        """
        return self._charge_increments

    @property
    def epsilon(self):
        """
        The VdW epsilon term of this VirtualSite
        """
        return self._epsilon

    @property
    def sigma(self):
        """
        The VdW sigma term of this VirtualSite
        """
        return self._sigma

    @property
    def rmin_half(self):
        """
        The VdW rmin_half term of this VirtualSite
        """
        rmin = 2.**(1. / 6) * self._sigma
        rmin_half = rmin / 2
        return rmin_half

    @property
    def name(self):
        """
        The name of this VirtualSite
        """
        return self._name

    @property
    def type(self):
        """The type of this VirtualSite (returns the class name as string)"""
        return self.__class__.__name__

    def __repr__(self):
        # TODO: Also include particle_index, which molecule this atom belongs to?
        return "VirtualSite(name={}, type={}, atoms={})".format(
            self.name, self.type, self.atoms)

    def __str__(self):
        # TODO: Also include particle_index, which molecule this atom belongs to?
        return "<VirtualSite name={} type={} atoms={}>".format(
            self.name, self.type, self.atoms)


class BondChargeVirtualSite(VirtualSite):
    """
    A particle representing a "Bond Charge"-type virtual site, in which the location of the charge is specified by the positions of two atoms. This supports placement of a virtual site S along a vector between two specified atoms, e.g. to allow for a sigma hole for halogens or similar contexts. With positive values of the distance, the virtual site lies outside the first indexed atom.

    .. warning :: This API is experimental and subject to change.
    """

    def __init__(self,
                 atoms,
                 distance,
                 charge_increments=None,
                 weights=None,
                 epsilon=None,
                 sigma=None,
                 rmin_half=None,
                 name=None):
        """
        Create a bond charge-type virtual site, in which the location of the charge is specified by the position of two atoms. This supports placement of a virtual site S along a vector between two specified atoms, e.g. to allow for a sigma hole for halogens or similar contexts. With positive values of the distance, the virtual site lies outside the first indexed atom.

        TODO: One of the examples on https://open-forcefield-toolkit.readthedocs.io/en/topology/smirnoff.html#virtualsites-virtual-sites-for-off-atom-charges has a BondCharge defined with three atoms -- How does that work?

        Parameters
        ----------
        atoms : list of openforcefield.topology.molecule.Atom objects of shape [N]
            The atoms defining the virtual site's position
        distance : float

        weights : list of floats of shape [N] or None, optional, default=None
            weights[index] is the weight of particles[index] contributing to the position of the virtual site. Default is None
        charge_increments : list of floats of shape [N], optional, default=None
            The amount of charge to remove from the VirtualSite's atoms and put in the VirtualSite. Indexing in this list should match the ordering in the atoms list. Default is None.
        epsilon : float
            Epsilon term for VdW properties of virtual site. Default is None.
        sigma : float, default=None
            Sigma term for VdW properties of virtual site. Default is None.
        rmin_half : float
            Rmin_half term for VdW properties of virtual site. Default is None.
        name : string or None, default=None
            The name of this virtual site. Default is None.
        """
        assert hasattr(distance, 'unit')
        assert unit.angstrom.is_compatible(distance.unit)

        super().__init__(
            atoms,
            charge_increments=charge_increments,
            epsilon=epsilon,
            sigma=sigma,
            rmin_half=rmin_half,
            name=name)
        self._distance = distance.in_units_of(unit.angstrom)

    def to_dict(self):
        vsite_dict = super().to_dict()
        vsite_dict['distance'] = quantity_to_string(self._distance)

        #type = self.type
        vsite_dict['vsite_type'] = self.type
        #vsite_dict['vsite_type'] = 'BondChargeVirtualSite'
        return vsite_dict

    @classmethod
    def from_dict(cls, vsite_dict):
        base_dict = deepcopy(vsite_dict)
        # Make sure it's the right type of virtual site
        assert vsite_dict['vsite_type'] == "BondChargeVirtualSite"
        base_dict.pop('vsite_type')
        base_dict.pop('distance')
        vsite = super().from_dict(**base_dict)
        vsite._distance = string_to_quantity(vsite_dict['distance'])
        return vsite

    @property
    def distance(self):
        """The distance parameter of the virtual site"""
        return self._distance


class _LonePairVirtualSite(VirtualSite):
    """Private base class for mono/di/trivalent lone pair virtual sites."""

    @classmethod
    def from_dict(cls, vsite_dict):
        base_dict = deepcopy(vsite_dict)

        # Make sure it's the right type of virtual site
        assert vsite_dict['vsite_type'] == cls.__name__
        base_dict.pop('vsite_type')
        base_dict.pop('distance')
        base_dict.pop('out_of_plane_angle')
        base_dict.pop('in_plane_angle')
        vsite = super().from_dict(**base_dict)
        vsite._distance = string_to_quantity(vsite_dict['distance'])
        vsite._in_plane_angle = string_to_quantity(
            vsite_dict['in_plane_angle'])
        vsite._out_of_plane_angle = string_to_quantity(
            vsite_dict['out_of_plane_angle'])
        return vsite


class MonovalentLonePairVirtualSite(VirtualSite):
    """
    A particle representing a "Monovalent Lone Pair"-type virtual site, in which the location of the charge is specified by the positions of three atoms. This is originally intended for situations like a carbonyl, and allows placement of a virtual site S at a specified distance d, in_plane_angle, and out_of_plane_angle relative to a central atom and two connected atoms.

    .. warning :: This API is experimental and subject to change.
   """

    def __init__(self,
                 atoms,
                 distance,
                 out_of_plane_angle,
                 in_plane_angle,
                 charge_increments=None,
                 weights=None,
                 epsilon=None,
                 sigma=None,
                 rmin_half=None,
                 name=None):
        """
        Create a bond charge-type virtual site, in which the location of the charge is specified by the position of three atoms.

        TODO : Do "weights" have any meaning here?

        Parameters
        ----------
        atoms : list of three openforcefield.topology.molecule.Atom objects
            The three atoms defining the virtual site's position
        distance : float

        out_of_plane_angle : float

        in_plane_angle : float

        epsilon : float
            Epsilon term for VdW properties of virtual site. Default is None.
        sigma : float, default=None
            Sigma term for VdW properties of virtual site. Default is None.
        rmin_half : float
            Rmin_half term for VdW properties of virtual site. Default is None.
        name : string or None, default=None
            The name of this virtual site. Default is None.


        """
        #assert isinstance(distance, unit.Quantity)
        # TODO: Check for proper number of atoms
        assert hasattr(distance, 'unit')
        assert unit.angstrom.is_compatible(distance.unit)
        assert hasattr(in_plane_angle, 'unit')
        assert unit.degree.is_compatible(in_plane_angle.unit)
        assert hasattr(out_of_plane_angle, 'unit')
        assert unit.degree.is_compatible(out_of_plane_angle.unit)

        assert len(atoms) == 3
        super().__init__(
            atoms,
            charge_increments=charge_increments,
            epsilon=epsilon,
            sigma=sigma,
            rmin_half=rmin_half,
            name=name)
        self._distance = distance.in_units_of(unit.angstrom)
        self._out_of_plane_angle = out_of_plane_angle.in_units_of(unit.degree)
        self._in_plane_angle = in_plane_angle.in_units_of(unit.degree)

    def to_dict(self):
        vsite_dict = super().to_dict()
        vsite_dict['distance'] = quantity_to_string(self._distance)
        vsite_dict['out_of_plane_angle'] = quantity_to_string(
            self._out_of_plane_angle)
        vsite_dict['in_plane_angle'] = quantity_to_string(self._in_plane_angle)
        #vsite_dict['vsite_type'] = self.type.fget()
        vsite_dict['vsite_type'] = self.type
        #vsite_dict['vsite_type'] = 'MonovalentLonePairVirtualSite'
        return vsite_dict

    @classmethod
    def from_dict(cls, vsite_dict):
        """
        Construct a new MonovalentLonePairVirtualSite from an serialized dictionary representation.

        Parameters
        ----------
        vsite_dict : dict
            The VirtualSite to deserialize.

        Returns
        -------
        The newly created MonovalentLonePairVirtualSite

        """
        # The function is overridden only to have a custom docstring.
        return super().from_dict(vsite_dict)

    @property
    def distance(self):
        """The distance parameter of the virtual site"""
        return self._distance

    @property
    def in_plane_angle(self):
        """The in_plane_angle parameter of the virtual site"""
        return self._in_plane_angle

    @property
    def out_of_plane_angle(self):
        """The out_of_plane_angle parameter of the virtual site"""
        return self._out_of_plane_angle


class DivalentLonePairVirtualSite(VirtualSite):
    """
    A particle representing a "Divalent Lone Pair"-type virtual site, in which the location of the charge is specified by the positions of three atoms. This is suitable for cases like four-point and five-point water models as well as pyrimidine; a charge site S lies a specified distance d from the central atom among three atoms along the bisector of the angle between the atoms (if out_of_plane_angle is zero) or out of the plane by the specified angle (if out_of_plane_angle is nonzero) with its projection along the bisector. For positive values of the distance d the virtual site lies outside the 2-1-3 angle and for negative values it lies inside.

    .. warning :: This API is experimental and subject to change.
    """

    def __init__(self,
                 atoms,
                 distance,
                 out_of_plane_angle,
                 in_plane_angle,
                 charge_increments=None,
                 weights=None,
                 epsilon=None,
                 sigma=None,
                 rmin_half=None,
                 name=None):
        """
        Create a divalent lone pair-type virtual site, in which the location of the charge is specified by the position of three atoms.

        TODO : Do "weights" have any meaning here?

        Parameters
        ----------
        atoms : list of 3 openforcefield.topology.molecule.Atom objects
            The three atoms defining the virtual site's position
        distance : float

        out_of_plane_angle : float

        in_plane_angle : float

        epsilon : float
            Epsilon term for VdW properties of virtual site. Default is None.
        sigma : float, default=None
            Sigma term for VdW properties of virtual site. Default is None.
        rmin_half : float
            Rmin_half term for VdW properties of virtual site. Default is None.
        name : string or None, default=None
            The name of this virtual site. Default is None.
        """
        #assert isinstance(distance, unit.Quantity)
        assert hasattr(distance, 'unit')
        assert unit.angstrom.is_compatible(distance.unit)
        assert hasattr(in_plane_angle, 'unit')
        assert unit.degree.is_compatible(in_plane_angle.unit)
        assert hasattr(out_of_plane_angle, 'unit')
        assert unit.degree.is_compatible(out_of_plane_angle.unit)
        assert len(atoms) == 3
        super().__init__(
            atoms,
            charge_increments=charge_increments,
            epsilon=epsilon,
            sigma=sigma,
            rmin_half=rmin_half,
            name=name)
        self._distance = distance.in_units_of(unit.angstrom)
        self._out_of_plane_angle = out_of_plane_angle.in_units_of(unit.degree)
        self._in_plane_angle = in_plane_angle.in_units_of(unit.degree)

    def to_dict(self):
        vsite_dict = super().to_dict()
        vsite_dict['distance'] = quantity_to_string(self._distance)
        vsite_dict['out_of_plane_angle'] = quantity_to_string(
            self._out_of_plane_angle)
        vsite_dict['in_plane_angle'] = quantity_to_string(self._in_plane_angle)
        vsite_dict['vsite_type'] = self.type
        return vsite_dict

    @classmethod
    def from_dict(cls, vsite_dict):
        """
        Construct a new DivalentLonePairVirtualSite from an serialized dictionary representation.

        Parameters
        ----------
        vsite_dict : dict
            The VirtualSite to deserialize.

        Returns
        -------
        The newly created DivalentLonePairVirtualSite

        """
        # The function is overridden only to have a custom docstring.
        return super().from_dict(vsite_dict)

    @property
    def distance(self):
        """The distance parameter of the virtual site"""
        return self._distance

    @property
    def in_plane_angle(self):
        """The in_plane_angle parameter of the virtual site"""
        return self._in_plane_angle

    @property
    def out_of_plane_angle(self):
        """The out_of_plane_angle parameter of the virtual site"""
        return self._out_of_plane_angle


class TrivalentLonePairVirtualSite(VirtualSite):
    """
    A particle representing a "Trivalent Lone Pair"-type virtual site, in which the location of the charge is specified by the positions of four atoms. This is suitable for planar or tetrahedral nitrogen lone pairs; a charge site S lies above the central atom (e.g. nitrogen a distance d along the vector perpendicular to the plane of the three connected atoms (2,3,4). With positive values of d the site lies above the nitrogen and with negative values it lies below the nitrogen.

    .. warning :: This API is experimental and subject to change.
    """

    def __init__(self,
                 atoms,
                 distance,
                 out_of_plane_angle,
                 in_plane_angle,
                 charge_increments=None,
                 weights=None,
                 epsilon=None,
                 sigma=None,
                 rmin_half=None,
                 name=None):
        """
        Create a trivalent lone pair-type virtual site, in which the location of the charge is specified by the position of four atoms.

        TODO : Do "weights" have any meaning here?

        Parameters
        ----------
        atoms : list of 4 openforcefield.topology.molecule.Atom objects
            The three atoms defining the virtual site's position
        distance : float

        out_of_plane_angle : float

        in_plane_angle : float

        epsilon : float
            Epsilon term for VdW properties of virtual site. Default is None.
        sigma : float, default=None
            Sigma term for VdW properties of virtual site. Default is None.
        rmin_half : float
            Rmin_half term for VdW properties of virtual site. Default is None.
        name : string or None, default=None
            The name of this virtual site. Default is None.

        """
        assert len(atoms) == 4
        assert hasattr(distance, 'unit')
        assert unit.angstrom.is_compatible(distance.unit)
        assert hasattr(in_plane_angle, 'unit')
        assert unit.degree.is_compatible(in_plane_angle.unit)
        assert hasattr(out_of_plane_angle, 'unit')
        assert unit.degree.is_compatible(out_of_plane_angle.unit)

        super().__init__(
            atoms,
            charge_increments=charge_increments,
            epsilon=epsilon,
            sigma=sigma,
            rmin_half=rmin_half,
            name=name)
        self._distance = distance.in_units_of(unit.angstrom)
        self._out_of_plane_angle = out_of_plane_angle.in_units_of(unit.degree)
        self._in_plane_angle = in_plane_angle.in_units_of(unit.degree)

    def to_dict(self):
        vsite_dict = super().to_dict()
        vsite_dict['distance'] = quantity_to_string(self._distance)
        vsite_dict['out_of_plane_angle'] = quantity_to_string(
            self._out_of_plane_angle)
        vsite_dict['in_plane_angle'] = quantity_to_string(self._in_plane_angle)
        vsite_dict['vsite_type'] = self.type
        return vsite_dict

    @classmethod
    def from_dict(cls, vsite_dict):
        """
        Construct a new TrivalentPairVirtualSite from an serialized dictionary representation.

        Parameters
        ----------
        vsite_dict : dict
            The VirtualSite to deserialize.


        Returns
        -------
        The newly created TrivalentLonePairVirtualSite

        """
        # The function is overridden only to have a custom docstring.
        return super().from_dict(vsite_dict)

    @property
    def distance(self):
        """The distance parameter of the virtual site"""
        return self._distance

    @property
    def in_plane_angle(self):
        """The in_plane_angle parameter of the virtual site"""
        return self._in_plane_angle

    @property
    def out_of_plane_angle(self):
        """The out_of_plane_angle parameter of the virtual site"""
        return self._out_of_plane_angle


# =============================================================================================
# Bond Stereochemistry
# =============================================================================================

#class BondStereochemistry(Serializable):
#"""
#Bond stereochemistry representation
#"""
#def __init__(self, stereo_type, neighbor1, neighbor2):
#    """
#
#    Parameters
#    ----------
#    stereo_type
#    neighbor1
#    neighbor2
#    """
#    assert isinstance(neighbor1, Atom)
#    assert isinstance(neighbor2, Atom)
#    # Use stereo_type @setter to check stereo type is a permitted value
#    self.stereo_type = stereo_type
#    self._neighbor1 = neighbor1
#    self._neighbor2 = neighbor2

#def to_dict(self):
#    bs_dict = OrderedDict()
#    bs_dict['stereo_type'] = self._stereo_type
#    bs_dict['neighbor1_index'] = self._neighbor1.molecule_atom_index
#    bs_dict['neighbor2_index'] = self._neighbor2.molecule_atom_index
#    return bs_dict

#classmethod
#def from_dict(cls, molecule, bs_dict):
#    neighbor1 = molecule.atoms[bs_dict['neighbor1_index']]
#    neighbor2 = molecule.atoms[bs_dict['neighbor2_index']]
#    return cls.__init__(bs_dict['stereo_type'], neighbor1, neighbor2)

#@property
#def stereo_type(self):
#    return self._stereo_type

#@stereo_type.setter
#def stereo_type(self, value):
#    assert (value == 'CIS') or (value == 'TRANS') or (value is None)
#    self._stereo_type = value

#@property
#def neighbor1(self):
#    return self._neighbor1

#@property
#def neighbor2(self):
#    return self._neighbor2

#@property
#def neighbors(self):
#    return (self._neighbor1, self._neighbor2)

# =============================================================================================
# Bond
# =============================================================================================


class Bond(Serializable):
    """
    Chemical bond representation.

    .. warning :: This API is experimental and subject to change.

    .. todo :: Allow bonds to have associated properties.

    Attributes
    ----------
    atom1, atom2 : openforcefield.topology.Atom
        Atoms involved in the bond
    bondtype : int
        Discrete bond type representation for the Open Forcefield aromaticity model
        TODO: Do we want to pin ourselves to a single standard aromaticity model?
    type : str
        String based bond type
    order : int
        Integral bond order
    fractional_bond_order : float, optional
        Fractional bond order, or None.


    .. warning :: This API is experimental and subject to change.
    """

    def __init__(self,
                 atom1,
                 atom2,
                 bond_order,
                 is_aromatic,
                 fractional_bond_order=None,
                 stereochemistry=None):
        """
        Create a new chemical bond.

        """
        assert type(atom1) == Atom
        assert type(atom2) == Atom
        assert atom1.molecule is atom2.molecule
        assert isinstance(atom1.molecule, FrozenMolecule)
        self._molecule = atom1.molecule

        self._atom1 = atom1
        self._atom2 = atom2

        atom1.add_bond(self)
        atom2.add_bond(self)
        # TODO: Check bondtype and fractional_bond_order are valid?
        # TODO: Dative bonds
        #self._type = bondtype
        self._fractional_bond_order = fractional_bond_order
        self._bond_order = bond_order
        self._is_aromatic = is_aromatic
        self._stereochemistry = stereochemistry

    def to_dict(self):
        """
        Return a dict representation of the bond.

        """
        bond_dict = OrderedDict()
        bond_dict['atom1'] = self.atom1.molecule_atom_index
        bond_dict['atom2'] = self.atom2.molecule_atom_index
        bond_dict['bond_order'] = self._bond_order
        bond_dict['is_aromatic'] = self._is_aromatic
        bond_dict['stereochemistry'] = self._stereochemistry
        bond_dict['fractional_bond_order'] = self._fractional_bond_order
        return bond_dict

    @classmethod
    def from_dict(cls, molecule, d):
        """Create a Bond from a dict representation."""
        # TODO
        d['molecule'] = molecule
        d['atom1'] = molecule.atoms[d['atom1']]
        d['atom2'] = molecule.atoms[d['atom2']]
        return cls(*d)

    @property
    def atom1(self):
        return self._atom1

    @property
    def atom2(self):
        return self._atom2

    @property
    def atom1_index(self):
        return self.molecule.atoms.index(self._atom1)

    @property
    def atom2_index(self):
        return self.molecule.atoms.index(self._atom2)

    @property
    def atoms(self):
        return (self._atom1, self._atom2)

    @property
    def bond_order(self):
        return self._bond_order

    @bond_order.setter
    def bond_order(self, value):
        self._bond_order = value

    @property
    def fractional_bond_order(self):
        return self._fractional_bond_order

    @fractional_bond_order.setter
    def fractional_bond_order(self, value):
        self._fractional_bond_order = value

    @property
    def stereochemistry(self):
        return self._stereochemistry

    @property
    def is_aromatic(self):
        return self._is_aromatic

    @property
    def molecule(self):
        return self._molecule

    @molecule.setter
    def molecule(self, value):
        """
        Sets the Bond's parent molecule. Can not be changed after assignment
        """
        assert self._molecule is None
        self._molecule = value

    @property
    def molecule_bond_index(self):
        """
        The index of this Bond within the the list of bonds in ``Molecules``.

        """
        if self._molecule is None:
            raise ValueError('This Atom does not belong to a Molecule object')
        return self._molecule.bonds.index(self)

    def __repr__(self):
        return f"Bond(atom1 index={self.atom1_index}, atom2 index={self.atom2_index})"

    def __str__(self):
        return f"<Bond atom1 index='{self.atom1_index}', atom2 index='{self.atom2_index}'>"


#=============================================================================================
# Molecule
#=============================================================================================

# TODO: How do we automatically trigger invalidation of cached properties if an ``Atom``, ``Bond``, or ``VirtualSite`` is modified,
#       rather than added/deleted via the API? The simplest resolution is simply to make them immutable.


class FrozenMolecule(Serializable):
    """
    Immutable chemical representation of a molecule, such as a small molecule or biopolymer.

    .. todo :: What other API calls would be useful for supporting biopolymers as small molecules? Perhaps iterating over chains and residues?

    Examples
    --------

    Create a molecule from a sdf file

    >>> from openforcefield.utils import get_data_file_path
    >>> sdf_filepath = get_data_file_path('molecules/ethanol.sdf')
    >>> molecule = FrozenMolecule.from_file(sdf_filepath)

    Convert to OpenEye OEMol object

    >>> oemol = molecule.to_openeye()

    Create a molecule from an OpenEye molecule

    >>> molecule = FrozenMolecule.from_openeye(oemol)

    Convert to RDKit Mol object

    >>> rdmol = molecule.to_rdkit()

    Create a molecule from an RDKit molecule

    >>> molecule = FrozenMolecule.from_rdkit(rdmol)

    Create a molecule from IUPAC name (requires the OpenEye toolkit)

    >>> molecule = FrozenMolecule.from_iupac('imatinib')

    Create a molecule from SMILES

    >>> molecule = FrozenMolecule.from_smiles('Cc1ccccc1')

    .. warning :: This API is experimental and subject to change.


    """

    def __init__(self,
                 other=None,
                 file_format=None,
                 toolkit_registry=GLOBAL_TOOLKIT_REGISTRY,
                 allow_undefined_stereo=False):
        """
        Create a new FrozenMolecule object

        .. todo ::

           * If a filename or file-like object is specified but the file contains more than one molecule, what is the proper behavior?
           Read just the first molecule, or raise an exception if more than one molecule is found?

           * Should we also support SMILES strings or IUPAC names for ``other``?

        Parameters
        ----------
        other : optional, default=None
            If specified, attempt to construct a copy of the Molecule from the specified object.
            This can be any one of the following:

            * a :class:`Molecule` object
            * a file that can be used to construct a :class:`Molecule` object
            * an ``openeye.oechem.OEMol``
            * an ``rdkit.Chem.rdchem.Mol``
            * a serialized :class:`Molecule` object
        file_format : str, optional, default=None
            If providing a file-like object, you must specify the format
            of the data. If providing a file, the file format will attempt
            to be guessed from the suffix.
        toolkit_registry : a :class:`ToolkitRegistry` or :class:`ToolkitWrapper` object, optional, default=GLOBAL_TOOLKIT_REGISTRY
            :class:`ToolkitRegistry` or :class:`ToolkitWrapper` to use for I/O operations
        allow_undefined_stereo : bool, default=False
            If loaded from a file and ``False``, raises an exception if
            undefined stereochemistry is detected during the molecule's
            construction.

        Examples
        --------

        Create an empty molecule:

        >>> empty_molecule = FrozenMolecule()

        Create a molecule from a file that can be used to construct a molecule,
        using either a filename or file-like object:

        >>> from openforcefield.utils import get_data_file_path
        >>> sdf_filepath = get_data_file_path('molecules/ethanol.sdf')
        >>> molecule = FrozenMolecule(sdf_filepath)
        >>> molecule = FrozenMolecule(open(sdf_filepath, 'r'), file_format='sdf')

        >>> import gzip
        >>> mol2_gz_filepath = get_data_file_path('molecules/toluene.mol2.gz')
        >>> molecule = FrozenMolecule(gzip.GzipFile(mol2_gz_filepath, 'r'), file_format='mol2')

        Create a molecule from another molecule:

        >>> molecule_copy = FrozenMolecule(molecule)

        Convert to OpenEye OEMol object

        >>> oemol = molecule.to_openeye()

        Create a molecule from an OpenEye molecule:

        >>> molecule = FrozenMolecule(oemol)

        Convert to RDKit Mol object

        >>> rdmol = molecule.to_rdkit()

        Create a molecule from an RDKit molecule:

        >>> molecule = FrozenMolecule(rdmol)

        Create a molecule from a serialized molecule object:

        >>> serialized_molecule = molecule.__getstate__()
        >>> molecule_copy = Molecule(serialized_molecule)

        """

        self._cached_smiles = None

        # Figure out if toolkit_registry is a whole registry, or just a single wrapper
        if isinstance(toolkit_registry, ToolkitRegistry):
            pass
        elif isinstance(toolkit_registry, ToolkitWrapper):
            toolkit = toolkit_registry
            toolkit_registry = ToolkitRegistry(toolkit_precedence=[])
            toolkit_registry.add_toolkit(toolkit)
        else:
            raise ValueError(
                "'toolkit_registry' must be either a ToolkitRegistry or a ToolkitWrapper"
            )

        if other is None:
            self._initialize()
        else:
            loaded = False
            if isinstance(
                    other,
                    openforcefield.topology.FrozenMolecule) and not (loaded):
                self._copy_initializer(other)
                loaded = True
            if isinstance(other,
                          openforcefield.topology.Molecule) and not (loaded):
                # TODO: This will need to be updated once FrozenMolecules and Molecules are significantly different
                self._copy_initializer(other)
                loaded = True
            if isinstance(other, OrderedDict) and not (loaded):
                self.__setstate__(other)
                loaded = True
            # Check through the toolkit registry to find a compatible wrapper for loading
            if not loaded:
                try:
                    result = toolkit_registry.call('from_object', other, allow_undefined_stereo=allow_undefined_stereo)
                except NotImplementedError:
                    pass
                else:
                    self._copy_initializer(result)
                    loaded = True
            # TODO: Make this compatible with file-like objects (I couldn't figure out how to make an oemolistream
            # from a fileIO object)
            if (isinstance(other, str)
                    or hasattr(other, 'read')) and not (loaded):
                mol = Molecule.from_file(
                    other,
                    file_format=file_format,
                    toolkit_registry=toolkit_registry,
                    allow_undefined_stereo=allow_undefined_stereo
                )  # returns a list only if multiple molecules are found
                if type(mol) == list:
                    raise ValueError(
                        'Specified file or file-like object must contain exactly one molecule'
                    )

                self._copy_initializer(mol)
                loaded = True
            if not (loaded):
                msg = 'Cannot construct openforcefield.topology.Molecule from {}\n'.format(
                    other)
                raise Exception(msg)

    @property
    def has_unique_atom_names(self):
        """True if the molecule has unique atom names, False otherwise."""
        unique_atom_names = set([atom.name for atom in self.atoms])
        if len(unique_atom_names) < self.n_atoms:
            return False
        return True

    def generate_unique_atom_names(self):
        """
        Generate unique atom names using element name and number of times that element has occurred
        e.g. 'C1', 'H1', 'O1', 'C2', ...

        """
        from collections import defaultdict
        element_counts = defaultdict(int)
        for atom in self.atoms:
            symbol = atom.element.symbol
            element_counts[symbol] += 1
            atom.name = symbol + str(element_counts[symbol])

    def _validate(self):
        """
        Validate the molecule, ensuring it has unique atom names

        """
        if not self.has_unique_atom_names:
            self.generate_unique_atom_names()

    ####################################################################################################
    # Safe serialization
    ####################################################################################################

    def to_dict(self):
        """
        Return a dictionary representation of the molecule.

        .. todo ::

           * Document the representation standard.
           * How do we do version control with this standard?

        Returns
        -------
        molecule_dict : OrderedDict
            A dictionary representation of the molecule.

        """
        molecule_dict = OrderedDict()
        molecule_dict['name'] = self._name
        ## From Jeff: If we go the properties-as-dict route, then _properties should, at
        ## the top level, be a dict. Should we go through recursively and ensure all values are dicts too?
        molecule_dict['atoms'] = [atom.to_dict() for atom in self._atoms]
        molecule_dict['virtual_sites'] = [
            vsite.to_dict() for vsite in self._virtual_sites
        ]
        molecule_dict['bonds'] = [bond.to_dict() for bond in self._bonds]
        # TODO: Charges
        # TODO: Properties
        # From Jeff: We could have the onerous requirement that all "properties" have to_dict() functions.
        # Or we could restrict properties to simple stuff (ints, strings, floats, and the like)
        # Or pickle anything unusual
        # Or not allow user-defined properties at all (just use our internal _cached_properties)
        #molecule_dict['properties'] = dict([(key, value._to_dict()) for key.value in self._properties])
        # TODO: Assuming "simple stuff" properties right now, figure out a better standard
        molecule_dict['properties'] = self._properties
        if hasattr(self, '_cached_properties'):
            molecule_dict['cached_properties'] = self._cached_properties
        # TODO: Conformers
        if self._conformers is None:
            molecule_dict['conformers'] = None
        else:
            molecule_dict['conformers'] = []
            molecule_dict[
                'conformers_unit'] = 'angstrom'  # Have this defined as a class variable?
            for conf in self._conformers:
                conf_unitless = (conf / unit.angstrom)
                conf_serialized, conf_shape = serialize_numpy((conf_unitless))
                molecule_dict['conformers'].append(conf_serialized)
        if self._partial_charges is None:
            molecule_dict['partial_charges'] = None
            molecule_dict['partial_charges_unit'] = None

        else:
            charges_unitless = self._partial_charges / unit.elementary_charge
            charges_serialized, charges_shape = serialize_numpy(
                charges_unitless)
            molecule_dict['partial_charges'] = charges_serialized
            molecule_dict['partial_charges_unit'] = 'elementary_charge'

        return molecule_dict

    def __hash__(self):
        """
        Returns a hash of this molecule. Used when checking molecule uniqueness in Topology creation.

        Returns
        -------
        string
        """
        return hash(self.to_smiles())

    @classmethod
    def from_dict(cls, molecule_dict):
        """
        Create a new Molecule from a dictionary representation

        Parameters
        ----------
        molecule_dict : OrderedDict
            A dictionary representation of the molecule.

        Returns
        -------
        molecule : Molecule
            A Molecule created from the dictionary representation

        """
        # This implementation is a compromise to let this remain as a classmethod
        mol = cls()
        mol._initialize_from_dict(molecule_dict)
        return mol

    def _initialize_from_dict(self, molecule_dict):
        """
        Initialize this Molecule from a dictionary representation

        Parameters
        ----------
        molecule_dict : OrderedDict
            A dictionary representation of the molecule.
        """
        # TODO: Provide useful exception messages if there are any failures

        self._initialize()
        self.name = molecule_dict['name']
        for atom_dict in molecule_dict['atoms']:
            self._add_atom(**atom_dict)

        # Handle virtual site unit reattachment and molecule tagging
        for vsite_dict in molecule_dict['virtual_sites']:
            vsite_dict_units = deepcopy(vsite_dict)

            # Attach units to epsilon term
            vsite_dict_units['epsilon'] = string_to_quantity(
                vsite_dict['epsilon'])
            vsite_dict_units['sigma'] = string_to_quantity(
                vsite_dict['sigma'])
            vsite_dict_units['charge_increments'] = string_to_quantity(
                vsite_dict['charge_increments'])

            # Call the correct molecule._add_X_virtual_site function, based on the stated type
            if vsite_dict_units['vsite_type'] == "BondChargeVirtualSite":
                del vsite_dict_units['vsite_type']
                vsite_dict_units['distance'] = string_to_quantity(
                    vsite_dict['distance'])
                self._add_bond_charge_virtual_site(**vsite_dict_units)

            elif vsite_dict_units[
                    'vsite_type'] == "MonovalentLonePairVirtualSite":
                del vsite_dict_units['vsite_type']
                vsite_dict_units['distance'] = string_to_quantity(
                    vsite_dict['distance'])
                vsite_dict_units['in_plane_angle'] = string_to_quantity(
                    vsite_dict['in_plane_angle'])
                vsite_dict_units['out_of_plane_angle'] = string_to_quantity(
                    vsite_dict['out_of_plane_angle'])
                self._add_monovalent_lone_pair_virtual_site(**vsite_dict_units)

            elif vsite_dict_units[
                    'vsite_type'] == "DivalentLonePairVirtualSite":
                del vsite_dict_units['vsite_type']
                vsite_dict_units['distance'] = string_to_quantity(
                    vsite_dict['distance'])
                vsite_dict_units['in_plane_angle'] = string_to_quantity(
                    vsite_dict['in_plane_angle'])
                vsite_dict_units['out_of_plane_angle'] = string_to_quantity(
                    vsite_dict['out_of_plane_angle'])
                self._add_divalent_lone_pair_virtual_site(**vsite_dict_units)

            elif vsite_dict_units[
                    'vsite_type'] == "TrivalentLonePairVirtualSite":
                del vsite_dict_units['vsite_type']
                vsite_dict_units['distance'] = string_to_quantity(
                    vsite_dict['distance'])
                vsite_dict_units['in_plane_angle'] = string_to_quantity(
                    vsite_dict['in_plane_angle'])
                vsite_dict_units['out_of_plane_angle'] = string_to_quantity(
                    vsite_dict['out_of_plane_angle'])
                self._add_trivalent_lone_pair_virtual_site(**vsite_dict_units)

            else:
                raise Exception("Vsite type {} not recognized".format(
                    vsite_dict['vsite_type']))

        for bond_dict in molecule_dict['bonds']:
            bond_dict['atom1'] = int(bond_dict['atom1'])
            bond_dict['atom2'] = int(bond_dict['atom2'])
            self._add_bond(**bond_dict)

        if molecule_dict['partial_charges'] is None:
            self._partial_charges = None
        else:
            charges_shape = (self.n_atoms, )
            partial_charges_unitless = deserialize_numpy(
                molecule_dict['partial_charges'], charges_shape)
            pc_unit = getattr(unit, molecule_dict['partial_charges_unit'])
            partial_charges = unit.Quantity(partial_charges_unitless, pc_unit)
            self._partial_charges = partial_charges

        if molecule_dict['conformers'] is None:
            self._conformers = None
        else:
            self._conformers = list()
            for ser_conf in molecule_dict['conformers']:
                # TODO: Update to use string_to_quantity
                conformers_shape = ((self.n_atoms, 3))
                conformer_unitless = deserialize_numpy(ser_conf,
                                                       conformers_shape)
                c_unit = getattr(unit, molecule_dict['conformers_unit'])
                conformer = unit.Quantity(conformer_unitless, c_unit)
                self._conformers.append(conformer)

        self._properties = molecule_dict['properties']

    def __repr__(self):
        """Return the SMILES of this molecule"""
        return "Molecule with name '{}' and SMILES '{}'".format(
            self.name, self.to_smiles())

    def __getstate__(self):
        return self.to_dict()

    def __setstate__(self, state):
        return self._initialize_from_dict(state)

    def _initialize(self):
        """
        Clear the contents of the current molecule.
        """
        self._name = ''
        self._atoms = list()
        self._virtual_sites = list()
        self._bonds = list()  # List of bonds between Atom objects
        self._properties = {}  # Attached properties to be preserved
        #self._cached_properties = None # Cached properties (such as partial charges) can be recomputed as needed
        self._partial_charges = None
        self._conformers = None  # Optional conformers

    def _copy_initializer(self, other):
        """
        Copy contents of the specified molecule

        .. todo :: Should this be a ``@staticmethod`` where we have an explicit copy constructor?

        Parameters
        ----------
        other : optional
            Overwrite the state of this FrozenMolecule with the specified FrozenMolecule object.
            A deep copy is made.

        """
        #assert isinstance(other, type(self)), "can only copy instances of {}".format(type(self))
        other_dict = other.to_dict()
        self._initialize_from_dict(other_dict)

    def __eq__(self, other):
        """Test two molecules for equality to see if they are the chemical species, but do not check other annotated properties.

        .. note ::

           Note that this method simply tests whether two molecules are identical chemical species using equivalence of their canonical isomeric SMILES.
           No effort is made to ensure that the atoms are in the same order or that any annotated properties are preserved.

        """
        # updated to use the new isomorphic checking method, with full matching
        # TODO the doc string did not match the previous function what matching should this method do?
        return Molecule.are_isomorphic(self, other, return_atom_map=False)[0]

    def to_smiles(self, toolkit_registry=GLOBAL_TOOLKIT_REGISTRY):
        """
        Return a canonical isomeric SMILES representation of the current molecule

        .. note :: RDKit and OpenEye versions will not necessarily return the same representation.

        Parameters
        ----------
        toolkit_registry : openforcefield.utils.toolkits.ToolkitRegistry or openforcefield.utils.toolkits.ToolkitWrapper, optional, default=None
            :class:`ToolkitRegistry` or :class:`ToolkitWrapper` to use for SMILES conversion

        Returns
        -------
        smiles : str
            Canonical isomeric explicit-hydrogen SMILES

        Examples
        --------

        >>> from openforcefield.utils import get_data_file_path
        >>> sdf_filepath = get_data_file_path('molecules/ethanol.sdf')
        >>> molecule = Molecule(sdf_filepath)
        >>> smiles = molecule.to_smiles()

        """
        # Initialize cached_smiles dict for this molecule if none exists
        if self._cached_smiles is None:
            self._cached_smiles = {}

        # Figure out which toolkit should be used to create the SMILES
        if isinstance(toolkit_registry, ToolkitRegistry):
            to_smiles_method = toolkit_registry.resolve('to_smiles')
        elif isinstance(toolkit_registry, ToolkitWrapper):
            to_smiles_method = toolkit_registry.to_smiles
        else:
            raise Exception(
                'Invalid toolkit_registry passed to to_smiles. Expected ToolkitRegistry or ToolkitWrapper. Got  {}'
                .format(type(toolkit_registry)))

        # Get a string representation of the function containing the toolkit name so we can check
        # if a SMILES was already cached for this molecule. This will return, for example
        # "RDKitToolkitWrapper.to_smiles"
        func_qualname = to_smiles_method.__qualname__

        # Check to see if a SMILES for this molecule was already cached using this method
        if func_qualname in self._cached_smiles:
            return self._cached_smiles[func_qualname]
        else:
            smiles = to_smiles_method(self)
            self._cached_smiles[func_qualname] = smiles
            return smiles

    @staticmethod
    def from_inchi(inchi, allow_undefined_stereo=False, toolkit_registry=GLOBAL_TOOLKIT_REGISTRY):
        """
        Construct a Molecule from a InChI representation

        Parameters
        ----------
        inchi : str
            The InChI representation of the molecule.

        allow_undefined_stereo : bool, default=False
            Whether to accept InChI with undefined stereochemistry. If False,
            an exception will be raised if a InChI with undefined stereochemistry
            is passed into this function.

        toolkit_registry : openforcefield.utils.toolkits.ToolRegistry or openforcefield.utils.toolkits.ToolkitWrapper, optional, default=None
            :class:`ToolkitRegistry` or :class:`ToolkitWrapper` to use for InChI-to-molecule conversion


        Returns
        -------
        molecule : openforcefield.topology.Molecule

        Examples
        --------
        make cis-1,2-Dichloroethene
        >>> molecule = Molecule.from_inchi('InChI=1S/C2H2Cl2/c3-1-2-4/h1-2H/b2-1-')
        """

        if isinstance(toolkit_registry, ToolkitRegistry):
            molecule = toolkit_registry.call('from_inchi',
                                             inchi,
                                             allow_undefined_stereo=allow_undefined_stereo)
        elif isinstance(toolkit_registry, ToolkitWrapper):
            toolkit = toolkit_registry
            molecule = toolkit.from_inchi(inchi,
                                          allow_undefined_stereo=allow_undefined_stereo)
        else:
            raise Exception(
                'Invalid toolkit_registry passed to from_inchi. Expected ToolkitRegistry or ToolkitWrapper. Got  {}'
                .format(type(toolkit_registry)))

        return molecule

    def to_inchi(self, fixed_hydrogens=False, toolkit_registry=GLOBAL_TOOLKIT_REGISTRY):
        """
        Create an InChI string for the molecule using the requested toolkit backend.
        InChI is a standardised representation that does not capture tautomers unless specified using the fixed hydrogen
        layer.

        For information on InChi see here https://iupac.org/who-we-are/divisions/division-details/inchi/

        Parameters
        ----------
        fixed_hydrogens: bool, default=False
            If a fixed hydrogen layer should be added to the InChI, if `True` this will produce a non standard specific
            InChI string of the molecule.

        toolkit_registry : openforcefield.utils.toolkits.ToolRegistry or openforcefield.utils.toolkits.ToolkitWrapper, optional, default=None
            :class:`ToolkitRegistry` or :class:`ToolkitWrapper` to use for molecule-to-InChI conversion

        Returns
        --------
        inchi: str
            The InChI string of the molecule.

        Raises
        -------
        InvalidToolkitError
             If an invalid object is passed as the toolkit_registry parameter
        """

        if isinstance(toolkit_registry, ToolkitRegistry):
            inchi = toolkit_registry.call('to_inchi',
                                          self,
                                          fixed_hydrogens=fixed_hydrogens)
        elif isinstance(toolkit_registry, ToolkitWrapper):
            toolkit = toolkit_registry
            inchi = toolkit.to_inchi(self,
                                     fixed_hydrogens=fixed_hydrogens)
        else:
            raise InvalidToolkitError(
                'Invalid toolkit_registry passed to to_inchi. Expected ToolkitRegistry or ToolkitWrapper. Got  {}'
                .format(type(toolkit_registry)))

        return inchi

    def to_inchikey(self, fixed_hydrogens=False, toolkit_registry=GLOBAL_TOOLKIT_REGISTRY):
        """
        Create an InChIKey for the molecule using the requested toolkit backend.
        InChIKey is a standardised representation that does not capture tautomers unless specified using the fixed hydrogen
        layer.

        For information on InChi see here https://iupac.org/who-we-are/divisions/division-details/inchi/

        Parameters
        ----------
        fixed_hydrogens: bool, default=False
            If a fixed hydrogen layer should be added to the InChI, if `True` this will produce a non standard specific
            InChI string of the molecule.

        toolkit_registry : openforcefield.utils.toolkits.ToolRegistry or openforcefield.utils.toolkits.ToolkitWrapper, optional, default=None
            :class:`ToolkitRegistry` or :class:`ToolkitWrapper` to use for molecule-to-InChIKey conversion

        Returns
        --------
        inchi_key: str
            The InChIKey representation of the molecule.

        Raises
        -------
        InvalidToolkitError
             If an invalid object is passed as the toolkit_registry parameter
        """

        if isinstance(toolkit_registry, ToolkitRegistry):
            inchi_key = toolkit_registry.call('to_inchikey',
                                              self,
                                              fixed_hydrogens=fixed_hydrogens)
        elif isinstance(toolkit_registry, ToolkitWrapper):
            toolkit = toolkit_registry
            inchi_key = toolkit.to_inchikey(self,
                                            fixed_hydrogens=fixed_hydrogens)
        else:
            raise InvalidToolkitError(
                'Invalid toolkit_registry passed to to_inchikey. Expected ToolkitRegistry or ToolkitWrapper. Got  {}'
                .format(type(toolkit_registry)))

        return inchi_key

    @staticmethod
    def from_smiles(smiles,
                    hydrogens_are_explicit=False,
                    toolkit_registry=GLOBAL_TOOLKIT_REGISTRY,
                    allow_undefined_stereo=False):
        """
        Construct a Molecule from a SMILES representation

        Parameters
        ----------
        smiles : str
            The SMILES representation of the molecule.
        hydrogens_are_explicit : bool, default = False
            If False, the cheminformatics toolkit will perform hydrogen addition
        toolkit_registry : openforcefield.utils.toolkits.ToolkitRegistry or openforcefield.utils.toolkits.ToolkitWrapper, optional, default=None
            :class:`ToolkitRegistry` or :class:`ToolkitWrapper` to use for SMILES-to-molecule conversion
        allow_undefined_stereo : bool, default=False
            Whether to accept SMILES with undefined stereochemistry. If False,
            an exception will be raised if a SMILES with undefined stereochemistry
            is passed into this function.

        Returns
        -------
        molecule : openforcefield.topology.Molecule

        Examples
        --------

        >>> molecule = Molecule.from_smiles('Cc1ccccc1')

        """
        if isinstance(toolkit_registry, ToolkitRegistry):
            molecule = toolkit_registry.call('from_smiles',
                                             smiles,
                                             hydrogens_are_explicit=hydrogens_are_explicit,
                                             allow_undefined_stereo=allow_undefined_stereo)
        elif isinstance(toolkit_registry, ToolkitWrapper):
            toolkit = toolkit_registry
            molecule = toolkit.from_smiles(smiles,
                                           hydrogens_are_explicit=hydrogens_are_explicit,
                                           allow_undefined_stereo=allow_undefined_stereo
                                           )
        else:
            raise Exception(
                'Invalid toolkit_registry passed to from_smiles. Expected ToolkitRegistry or ToolkitWrapper. Got  {}'
                .format(type(toolkit_registry)))

        return molecule

    @staticmethod
    def are_isomorphic(
            mol1, mol2, return_atom_map=False,
            aromatic_matching=True,
            formal_charge_matching=True,
            bond_order_matching=True,
            atom_stereochemistry_matching=True,
            bond_stereochemistry_matching=True
    ):
        """
        Determines whether the two molecules are isomorphic by comparing their graph representations and the chosen
        node/edge attributes. Minimally connections and atomic_number are checked.

        If nx.Graphs() are given they must at least have atomic_number attributes on nodes.
        other optional attributes for nodes are: is_aromatic, formal_charge and stereochemistry.
        optional attributes for edges are: is_aromatic, bond_order and stereochemistry.

        .. warning :: This API is experimental and subject to change.

        Parameters
        ----------
        mol1 : an openforcefield.topology.molecule.FrozenMolecule or TopologyMolecule or nx.Graph()
        mol2 : an openforcefield.topology.molecule.FrozenMolecule or TopologyMolecule or nx.Graph()
            The molecule to test for isomorphism.

        return_atom_map: bool, default=False, optional
            will return an optional dict containing the atomic mapping.

        aromatic_matching: bool, default=True, optional
            compare the aromatic attributes of bonds and atoms.

        formal_charge_matching: bool, default=True, optional
            compare the formal charges attributes of the atoms.

        bond_order_matching: bool, deafult=True, optional
            compare the bond order on attributes of the bonds.

        atom_stereochemistry_matching : bool, default=True, optional
            If ``False``, atoms' stereochemistry is ignored for the
            purpose of determining equality.

        bond_stereochemistry_matching : bool, default=True, optional
            If ``False``, bonds' stereochemistry is ignored for the
            purpose of determining equality.

        Returns
        -------
        molecules_are_isomorphic : bool

        atom_map : default=None, Optional,
            [Dict[int,int]] ordered by mol1 indexing {mol1_index: mol2_index}
            If molecules are not isomorphic given input arguments, will return None instead of dict.
        """

        # Do a quick hill formula check first
        if Molecule.to_hill_formula(mol1) != Molecule.to_hill_formula(mol2):
            return False, None

        # Build the user defined matching functions
        def node_match_func(x, y):
            # always match by atleast atomic number
            is_equal = (x['atomic_number'] == y['atomic_number'])
            if aromatic_matching:
                is_equal &= (x['is_aromatic'] == y['is_aromatic'])
            if formal_charge_matching:
                is_equal &= (x['formal_charge'] == y['formal_charge'])
            if atom_stereochemistry_matching:
                is_equal &= (x['stereochemistry'] == y['stereochemistry'])
            return is_equal

        # check if we want to do any bond matching if not the function is None
        if aromatic_matching or bond_order_matching or bond_stereochemistry_matching:
            def edge_match_func(x, y):
                # We don't need to check the exact bond order (which is 1 or 2)
                # if the bond is aromatic. This way we avoid missing a match only
                # if the alternate bond orders 1 and 2 are assigned differently.
                if aromatic_matching and bond_order_matching:
                    is_equal = (x['is_aromatic'] == y['is_aromatic']) or (x['bond_order'] == y['bond_order'])
                elif aromatic_matching:
                    is_equal = (x['is_aromatic'] == y['is_aromatic'])
                elif bond_order_matching:
                    is_equal = (x['bond_order'] == y['bond_order'])
                else:
                    is_equal = None
                if bond_stereochemistry_matching:
                    if is_equal is None:
                        is_equal = (x['stereochemistry'] == y['stereochemistry'])
                    else:
                        is_equal &= (x['stereochemistry'] == y['stereochemistry'])

                return is_equal
        else:
            edge_match_func = None

        # Here we should work out what data type we have, also deal with lists?
        def to_networkx(data):
            """For the given data type, return the networkx graph"""
            from openforcefield.topology import TopologyMolecule

            if isinstance(data, FrozenMolecule):
                # Molecule class instance
                return data.to_networkx()
            elif isinstance(data, TopologyMolecule):
                # TopologyMolecule class instance
                return data.reference_molecule.to_networkx()
            elif isinstance(data, nx.Graph):
                return data

            else:
                raise NotImplementedError(f'The input type {type(data)} is not supported,'
                                          f'please supply an openforcefield.topology.molecule.Molecule,'
                                          f'openforcefield.topology.topology.TopologyMolecule or networkx representaion '
                                          f'of the molecule.')

        mol1_netx = to_networkx(mol1)
        mol2_netx = to_networkx(mol2)
        isomorphic = nx.is_isomorphic(mol1_netx,
                                      mol2_netx,
                                      node_match=node_match_func,
                                      edge_match=edge_match_func)

        if isomorphic and return_atom_map:
            # now generate the sorted mapping between the molecules
            GM = GraphMatcher(
                mol1_netx,
                mol2_netx,
                node_match=node_match_func,
                edge_match=edge_match_func)
            for mapping in GM.isomorphisms_iter():
                topology_atom_map = mapping
                break

            # reorder the mapping by keys
            sorted_mapping = {}
            for key in sorted(topology_atom_map.keys()):
                sorted_mapping[key] = topology_atom_map[key]

            return isomorphic, sorted_mapping

        else:
            return isomorphic, None

    def is_isomorphic_with(self, other, **kwargs):
        """
        Check if the molecule is isomorphic with the other molecule which can be an openforcefield.topology.Molecule,
        or TopologyMolecule or nx.Graph(). Full matching is done using the options described bellow.

        .. warning :: This API is experimental and subject to change.

        Parameters
        ----------
        other: openforcefield.topology.Molecule or TopologyMolecule or nx.Graph()

        return_atom_map: bool, default=False, optional
            will return an optional dict containing the atomic mapping.

        aromatic_matching: bool, default=True, optional
        compare the aromatic attributes of bonds and atoms.

        formal_charge_matching: bool, default=True, optional
        compare the formal charges attributes of the atoms.

        bond_order_matching: bool, deafult=True, optional
        compare the bond order on attributes of the bonds.

        atom_stereochemistry_matching : bool, default=True, optional
            If ``False``, atoms' stereochemistry is ignored for the
            purpose of determining equality.

        bond_stereochemistry_matching : bool, default=True, optional
            If ``False``, bonds' stereochemistry is ignored for the
            purpose of determining equality.

        Returns
        -------
        isomorphic : bool
        """

        return Molecule.are_isomorphic(self, other, return_atom_map=False,
                                       aromatic_matching=kwargs.get('aromatic_matching', True),
                                       formal_charge_matching=kwargs.get('formal_charge_matching', True),
                                       bond_order_matching=kwargs.get('bond_order_matching', True),
                                       atom_stereochemistry_matching=kwargs.get('atom_stereochemistry_matching', True),
                                       bond_stereochemistry_matching=kwargs.get('bond_stereochemistry_matching', True))[0]

    def generate_conformers(self,
                            toolkit_registry=GLOBAL_TOOLKIT_REGISTRY,
                            n_conformers=10,
                            clear_existing=True):
        """
        Generate conformers for this molecule using an underlying toolkit

        Parameters
        ----------
        toolkit_registry : openforcefield.utils.toolkits.ToolkitRegistry or openforcefield.utils.toolkits.ToolkitWrapper, optional, default=None
            :class:`ToolkitRegistry` or :class:`ToolkitWrapper` to use for SMILES-to-molecule conversion
        n_conformers : int, default=1
            The maximum number of conformers to produce
        clear_existing : bool, default=True
            Whether to overwrite existing conformers for the molecule

        Examples
        --------

        >>> molecule = Molecule.from_smiles('CCCCCC')
        >>> molecule.generate_conformers()

        Raises
        ------
        InvalidToolkitError
            If an invalid object is passed as the toolkit_registry parameter

        """
        if isinstance(toolkit_registry, ToolkitRegistry):
            return toolkit_registry.call('generate_conformers', self, n_conformers=n_conformers,
                                         clear_existing=clear_existing)
        elif isinstance(toolkit_registry, ToolkitWrapper):
            toolkit = toolkit_registry
            return toolkit.generate_conformers(self, n_conformers=n_conformers, clear_existing=clear_existing)
        else:
            raise InvalidToolkitError(
                'Invalid toolkit_registry passed to generate_conformers. Expected ToolkitRegistry or ToolkitWrapper. Got  {}'
                .format(type(toolkit_registry)))

    def compute_partial_charges_am1bcc(self, toolkit_registry=GLOBAL_TOOLKIT_REGISTRY):
        """
        Calculate partial atomic charges for this molecule using AM1-BCC run by an underlying toolkit

        Parameters
        ----------
        toolkit_registry : openforcefield.utils.toolkits.ToolkitRegistry or openforcefield.utils.toolkits.ToolkitWrapper, optional, default=None
            :class:`ToolkitRegistry` or :class:`ToolkitWrapper` to use for the calculation

        Examples
        --------

        >>> molecule = Molecule.from_smiles('CCCCCC')
        >>> molecule.generate_conformers()
        >>> molecule.compute_partial_charges_am1bcc()

        Raises
        ------
        InvalidToolkitError
            If an invalid object is passed as the toolkit_registry parameter

        """
        if isinstance(toolkit_registry, ToolkitRegistry):
            charges = toolkit_registry.call(
                      'compute_partial_charges_am1bcc',
                      self
            )
        elif isinstance(toolkit_registry, ToolkitWrapper):
            toolkit = toolkit_registry
            charges = toolkit.compute_partial_charges_am1bcc(self)
        else:
            raise InvalidToolkitError(
                'Invalid toolkit_registry passed to compute_partial_charges_am1bcc. Expected ToolkitRegistry or ToolkitWrapper. Got  {}'
                .format(type(toolkit_registry)))
        self.partial_charges = charges

    def compute_partial_charges(self,
                                #quantum_chemical_method='AM1-BCC',
                                #partial_charge_method='None',
                                toolkit_registry=GLOBAL_TOOLKIT_REGISTRY):
        """
        **Warning! Not Implemented!**
        Calculate partial atomic charges for this molecule using an underlying toolkit

        Parameters
        ----------
        quantum_chemical_method : string, default='AM1-BCC'
            The quantum chemical method to use for partial charge calculation.
        partial_charge_method : string, default='None'
            The partial charge calculation method to use for partial charge calculation.
        toolkit_registry : openforcefield.utils.toolkits.ToolkitRegistry or openforcefield.utils.toolkits.ToolkitWrapper, optional, default=None
            :class:`ToolkitRegistry` or :class:`ToolkitWrapper` to use for SMILES-to-molecule conversion

        Examples
        --------

        >>> molecule = Molecule.from_smiles('CCCCCC')
        >>> molecule.generate_conformers()

        Raises
        ------
        InvalidToolkitError
            If an invalid object is passed as the toolkit_registry parameter

        """
        raise NotImplementedError
        # TODO: Implement this in a way that's compliant with SMIRNOFF's <ChargeIncrementModel> tag when the spec gets finalized
        # if isinstance(toolkit_registry, ToolkitRegistry):
        #     charges = toolkit_registry.call(
        #               'compute_partial_charges_am1bcc',
        #               self,
        #     )
        # elif isinstance(toolkit_registry, ToolkitWrapper):
        #     toolkit = toolkit_registry
        #     charges = toolkit.compute_partial_charges_am1bcc(
        #         self,
        #         #quantum_chemical_method=quantum_chemical_method,
        #         #partial_charge_method=partial_charge_method
        #     )
        # else:
        #     raise InvalidToolkitError(
        #         'Invalid toolkit_registry passed to compute_partial_charges_am1bcc. Expected ToolkitRegistry or ToolkitWrapper. Got  {}'
        #         .format(type(toolkit_registry)))

    def assign_fractional_bond_orders(self,
                                      bond_order_model=None,
                                      toolkit_registry=GLOBAL_TOOLKIT_REGISTRY,
                                      use_conformers=None):
        """
        Update and store list of bond orders this molecule. Bond orders are stored on each
        bond, in the `bond.fractional_bond_order` attribute.

        .. warning :: This API is experimental and subject to change.

        Parameters
        ----------
        toolkit_registry : openforcefield.utils.toolkits.ToolkitRegistry or openforcefield.utils.toolkits.ToolkitWrapper, optional, default=None
            :class:`ToolkitRegistry` or :class:`ToolkitWrapper` to use for SMILES-to-molecule conversion
        bond_order_model : string, optional. Default=None
            The bond order model to use for fractional bond order calculation. If None, "am1-wiberg" will be used.
        use_conformers : iterable of simtk.unit.Quantity(np.array) with shape (n_atoms, 3) and dimension of distance, optional, default=None
            The conformers to use for fractional bond order calculation. If None, an appropriate number
            of conformers will be generated by an available ToolkitWrapper.

        Examples
        --------

        >>> molecule = Molecule.from_smiles('CCCCCC')
        >>> molecule.assign_fractional_bond_orders()

        Raises
        ------
        InvalidToolkitError
            If an invalid object is passed as the toolkit_registry parameter

        """
        if isinstance(toolkit_registry, ToolkitRegistry):
            return toolkit_registry.call(
                'assign_fractional_bond_orders',
                self,
                bond_order_model=bond_order_model,
                use_conformers=use_conformers)
        elif isinstance(toolkit_registry, ToolkitWrapper):
            toolkit = toolkit_registry
            return toolkit.assign_fractional_bond_orders(
                self,
                bond_order_model=bond_order_model,
                use_conformers=use_conformers)
        else:
            raise Exception(
                f'Invalid toolkit_registry passed to assign_fractional_bond_orders. '
                f'Expected ToolkitRegistry or ToolkitWrapper. Got {type(toolkit_registry)}.')


    def _invalidate_cached_properties(self):
        """
        Indicate that the chemical entity has been altered.
        """
        #if hasattr(self, '_cached_properties'):
        #    delattr(self, '_cached_properties')
        self._conformers = None
        self._partial_charges = None
        self._propers = None
        self._impropers = None

        self._cached_smiles = None
        # TODO: Clear fractional bond orders

    def to_networkx(self):
        """Generate a NetworkX undirected graph from the Molecule.

        Nodes are Atoms labeled with particle indices and atomic elements (via the ``element`` node atrribute).
        Edges denote chemical bonds between Atoms.
        Virtual sites are not included, since they lack a concept of chemical connectivity.

        .. todo ::

           * Do we need a ``from_networkx()`` method? If so, what would the Graph be required to provide?
           * Should edges be labeled with discrete bond types in some aromaticity model?
           * Should edges be labeled with fractional bond order if a method is specified?
           * Should we add other per-atom and per-bond properties (e.g. partial charges) if present?
           * Can this encode bond/atom chirality?


        Returns
        -------
        graph : networkx.Graph
            The resulting graph, with nodes (atoms) labeled with atom indices, elements, stereochemistry and aromaticity
            flags and bonds with two atom indices, bond order, stereochemistry, and aromaticity flags

        Examples
        --------
        Retrieve the bond graph for imatinib (OpenEye toolkit required)

        >>> molecule = Molecule.from_iupac('imatinib')
        >>> nxgraph = molecule.to_networkx()

        """
        import networkx as nx
        G = nx.Graph()
        for atom in self.atoms:
            G.add_node(
                atom.molecule_atom_index, atomic_number=atom.atomic_number, is_aromatic=atom.is_aromatic,
                stereochemistry=atom.stereochemistry, formal_charge=atom.formal_charge)
            #G.add_node(atom.molecule_atom_index, attr_dict={'atomic_number': atom.atomic_number})
        for bond in self.bonds:
            G.add_edge(
                bond.atom1_index, bond.atom2_index, bond_order=bond.bond_order, is_aromatic=bond.is_aromatic,
                stereochemistry=bond.stereochemistry)
            #G.add_edge(bond.atom1_index, bond.atom2_index, attr_dict={'order':bond.bond_order})

        return G

    def find_rotatable_bonds(self, ignore_functional_groups=None, toolkit_registry=GLOBAL_TOOLKIT_REGISTRY):
        """
        Find all bonds classed as rotatable ignoring any matched to the ``ignore_functional_groups`` list.

        Parameters
        ----------
        ignore_functional_groups: optional, List[str], default=None,
            A list of bond SMARTS patterns to be ignored when finding rotatable bonds.

        toolkit_registry: openforcefield.utils.toolkits.ToolkitRegistry or openforcefield.utils.toolkits.ToolkitWrapper, optional, default=None
            :class:`ToolkitRegistry` or :class:`ToolkitWrapper` to use for SMARTS matching

        Returns
        -------
        bonds: List[openforcefield.topology.molecule.Bond]
            The list of openforcefield.topology.molecule.Bond instances which are rotatable.
        """

        # general rotatable bond smarts taken from RDKit
        # https://github.com/rdkit/rdkit/blob/1bf6ef3d65f5c7b06b56862b3fb9116a3839b229/rdkit/Chem/Lipinski.py#L47%3E
        rotatable_bond_smarts = '[!$(*#*)&!D1:1]-&!@[!$(*#*)&!D1:2]'

        # get all of the general matches
        general_matches = self.chemical_environment_matches(query=rotatable_bond_smarts,
                                                            toolkit_registry=toolkit_registry)

        # this will give all forwards and backwards matches, so condense them down with this function
        def condense_matches(matches):
            condensed_matches = set()
            for m in matches:
                condensed_matches.add(tuple(sorted(m)))
            return condensed_matches

        general_bonds = condense_matches(general_matches)

        # now refine the list using the ignore groups
        if ignore_functional_groups is not None:
            matches_to_ignore = set()

            # make ignore_functional_groups an iterable object
            if isinstance(ignore_functional_groups, str):
                ignore_functional_groups = [ignore_functional_groups]
            else:
                try:
                    iter(ignore_functional_groups)
                except TypeError:
                    ignore_functional_groups = [ignore_functional_groups]

            # find the functional groups to remove
            for functional_group in ignore_functional_groups:
                # note I run the searches through this function so they have to be SMIRKS?
                ignore_matches = self.chemical_environment_matches(query=functional_group,
                                                                   toolkit_registry=toolkit_registry)
                ignore_matches = condense_matches(ignore_matches)
                # add the new matches to the matches to ignore
                matches_to_ignore.update(ignore_matches)

            # now remove all the matches
            for match in matches_to_ignore:
                try:
                    general_bonds.remove(match)
                # if the key is not in the list, the ignore pattern was not valid
                except KeyError:
                    continue

        # gather a list of bond instances to return
        rotatable_bonds = [self.get_bond_between(*bond) for bond in general_bonds]
        return rotatable_bonds

    def _add_atom(self,
                  atomic_number,
                  formal_charge,
                  is_aromatic,
                  stereochemistry=None,
                  name=None):
        """
        Add an atom

        Parameters
        ----------
        atomic_number : int
            Atomic number of the atom
        formal_charge : int
            Formal charge of the atom
        is_aromatic : bool
            If True, atom is aromatic; if False, not aromatic
        stereochemistry : str, optional, default=None
            Either 'R' or 'S' for specified stereochemistry, or None if stereochemistry is irrelevant
        name : str, optional, default=None
            An optional name for the atom

        Returns
        -------
        index : int
            The index of the atom in the molecule

        Examples
        --------

        Define a methane molecule

        >>> molecule = Molecule()
        >>> molecule.name = 'methane'
        >>> C = molecule.add_atom(6, 0, False)
        >>> H1 = molecule.add_atom(1, 0, False)
        >>> H2 = molecule.add_atom(1, 0, False)
        >>> H3 = molecule.add_atom(1, 0, False)
        >>> H4 = molecule.add_atom(1, 0, False)
        >>> bond_idx = molecule.add_bond(C, H1, False, 1)
        >>> bond_idx = molecule.add_bond(C, H2, False, 1)
        >>> bond_idx = molecule.add_bond(C, H3, False, 1)
        >>> bond_idx = molecule.add_bond(C, H4, False, 1)

        """
        # Create an atom
        atom = Atom(
            atomic_number,
            formal_charge,
            is_aromatic,
            stereochemistry=stereochemistry,
            name=name,
            molecule=self)
        self._atoms.append(atom)
        #self._particles.append(atom)
        self._invalidate_cached_properties()
        return self._atoms.index(atom)

    def _add_bond_charge_virtual_site(self, atoms, distance, **kwargs):
        """
        Create a bond charge-type virtual site, in which the location of the charge is specified by the position of two
        atoms. This supports placement of a virtual site S along a vector between two specified atoms, e.g. to allow
        for a sigma hole for halogens or similar contexts. With positive values of the distance, the virtual site lies
        outside the first indexed atom.

        Parameters
        ----------
        atoms : list of openforcefield.topology.molecule.Atom objects of shape [N]
            The atoms defining the virtual site's position
        distance : float

        weights : list of floats of shape [N] or None, optional, default=None
            weights[index] is the weight of particles[index] contributing to the position of the virtual site. Default
            is None
        charge_increments : list of floats of shape [N], optional, default=None
            The amount of charge to remove from the VirtualSite's atoms and put in the VirtualSite. Indexing in this
            list should match the ordering in the atoms list. Default is None.
        epsilon : float
            Epsilon term for VdW properties of virtual site. Default is None.
        sigma : float, default=None
            Sigma term for VdW properties of virtual site. Default is None.
        rmin_half : float
            Rmin_half term for VdW properties of virtual site. Default is None.
        name : string or None, default=None
            The name of this virtual site. Default is None.

        Returns
        -------
        index : int
            The index of the newly-added virtual site in the molecule
        """
        # Check if function was passed list of atoms or atom indices
        if all([isinstance(atom, int) for atom in atoms]):
            atom_list = [self.atoms[atom_index] for atom_index in atoms]
        elif all([isinstance(atom, Atom) for atom in atoms]):
            atom_list = atoms
        else:
            raise Exception(
                'Invalid inputs to molecule._add_bond_charge_virtual_site.'
                ' Expected ints or Atoms. Received types {} '.format(
                    [type(i) for i in atoms]))
        # TODO: Check to make sure bond does not already exist
        vsite = BondChargeVirtualSite(atom_list, distance, **kwargs)
        self._virtual_sites.append(vsite)
        self._invalidate_cached_properties()
        return self._virtual_sites.index(vsite)

    def _add_monovalent_lone_pair_virtual_site(self, atoms, distance,
                                               out_of_plane_angle,
                                               in_plane_angle, **kwargs):
        """
        Create a bond charge-type virtual site, in which the location of the charge is specified by the position of
        three atoms.

        TODO : Do "weights" have any meaning here?

        Parameters
        ----------
        atoms : list of three openforcefield.topology.molecule.Atom objects
            The three atoms defining the virtual site's position
        distance : float

        out_of_plane_angle : float

        in_plane_angle : float

        epsilon : float
            Epsilon term for VdW properties of virtual site. Default is None.
        sigma : float, default=None
            Sigma term for VdW properties of virtual site. Default is None.
        rmin_half : float
            Rmin_half term for VdW properties of virtual site. Default is None.
        name : string or None, default=None
            The name of this virtual site. Default is None.

        Returns
        -------
        index : int
            The index of the newly-added virtual site in the molecule
        """
        # Check if function was passed list of atoms or atom indices
        if all([isinstance(atom, int) for atom in atoms]):
            atom_list = [self.atoms[atom_index] for atom_index in atoms]
        elif all([isinstance(atom, Atom) for atom in atoms]):
            atom_list = atoms
        else:
            raise Exception(
                'Invalid inputs to molecule._add_monovalent_lone_pair_virtual_site. Expected ints or Atoms.'
                ' Received types {} '.format([type(i) for i in atoms]))
        # TODO: Check to make sure bond does not already exist
        vsite = MonovalentLonePairVirtualSite(
            atom_list, distance, out_of_plane_angle, in_plane_angle, **kwargs)
        self._virtual_sites.append(vsite)
        self._invalidate_cached_properties()
        return self._virtual_sites.index(vsite)

    def _add_divalent_lone_pair_virtual_site(self, atoms, distance,
                                             out_of_plane_angle,
                                             in_plane_angle, **kwargs):
        """
        Create a divalent lone pair-type virtual site, in which the location of the charge is specified by the position
        of three atoms.

        TODO : Do "weights" have any meaning here?

        Parameters
        ----------
        atoms : list of 3 openforcefield.topology.molecule.Atom objects
            The three atoms defining the virtual site's position
        distance : float

        out_of_plane_angle : float

        in_plane_angle : float

        epsilon : float
            Epsilon term for VdW properties of virtual site. Default is None.
        sigma : float, default=None
            Sigma term for VdW properties of virtual site. Default is None.
        rmin_half : float
            Rmin_half term for VdW properties of virtual site. Default is None.
        name : string or None, default=None
            The name of this virtual site. Default is None.

        Returns
        -------
        index : int
            The index of the newly-added virtual site in the molecule
        """
        # Check if function was passed list of atoms or atom indices
        if all([isinstance(atom, int) for atom in atoms]):
            atom_list = [self.atoms[atom_index] for atom_index in atoms]
        elif all([isinstance(atom, Atom) for atom in atoms]):
            atom_list = atoms
        else:
            raise Exception(
                'Invalid inputs to molecule._add_divalent_lone_pair_virtual_site. Expected ints or Atoms. '
                'Received types {} '.format([type(i) for i in atoms]))
        # TODO: Check to make sure bond does not already exist
        vsite = DivalentLonePairVirtualSite(
            atom_list, distance, out_of_plane_angle, in_plane_angle, **kwargs)
        self._virtual_sites.append(vsite)
        self._invalidate_cached_properties()
        return self._virtual_sites.index(vsite)

    def _add_trivalent_lone_pair_virtual_site(self, atoms, distance,
                                              out_of_plane_angle,
                                              in_plane_angle, **kwargs):
        """
        Create a trivalent lone pair-type virtual site, in which the location of the charge is specified by the position
         of four atoms.

        TODO : Do "weights" have any meaning here?

        Parameters
        ----------
        atoms : list of 4 openforcefield.topology.molecule.Atom objects or atom indices
            The three atoms defining the virtual site's position
        distance : float

        out_of_plane_angle : float

        in_plane_angle : float

        epsilon : float
            Epsilon term for VdW properties of virtual site. Default is None.
        sigma : float, default=None
            Sigma term for VdW properties of virtual site. Default is None.
        rmin_half : float
            Rmin_half term for VdW properties of virtual site. Default is None.
        name : string or None, default=None
            The name of this virtual site. Default is None.
        """
        # Check if function was passed list of atoms or atom indices
        if all([isinstance(atom, int) for atom in atoms]):
            atom_list = [self.atoms[atom_index] for atom_index in atoms]
        elif all([isinstance(atom, Atom) for atom in atoms]):
            atom_list = atoms
        else:
            raise Exception(
                'Invalid inputs to molecule._add_trivalent_lone_pair_virtual_site. Expected ints or Atoms. Received types {} '
                .format([type(i) for i in atoms]))
        vsite = TrivalentLonePairVirtualSite(
            atom_list, distance, out_of_plane_angle, in_plane_angle, **kwargs)
        self._virtual_sites.append(vsite)
        self._invalidate_cached_properties()
        return self._virtual_sites.index(vsite)

    def _add_bond(self,
                  atom1,
                  atom2,
                  bond_order,
                  is_aromatic,
                  stereochemistry=None,
                  fractional_bond_order=None):
        """
        Add a bond between two specified atom indices

        Parameters
        ----------
        atom1 : int or openforcefield.topology.molecule.Atom
            Index of first atom or first atom
        atom2_index : int or openforcefield.topology.molecule.Atom
            Index of second atom or second atom
        bond_order : int
            Integral bond order of Kekulized form
        is_aromatic : bool
            True if this bond is aromatic, False otherwise
        stereochemistry : str, optional, default=None
            Either 'E' or 'Z' for specified stereochemistry, or None if stereochemistry is irrelevant
        fractional_bond_order : float, optional, default=None
            The fractional (eg. Wiberg) bond order
        Returns
        -------
        index : int
            The index of the bond in the molecule

        """
        if isinstance(atom1, int) and isinstance(atom2, int):
            atom1_atom = self.atoms[atom1]
            atom2_atom = self.atoms[atom2]
        elif isinstance(atom1, Atom) and isinstance(atom2, Atom):
            atom1_atom = atom1
            atom2_atom = atom2
        else:
            raise Exception(
                'Invalid inputs to molecule._add_bond. Expected ints or Atoms. '
                'Received {} (type {}) and {} (type {}) '.format(
                    atom1, type(atom1), atom2, type(atom2)))
        # TODO: Check to make sure bond does not already exist
        if atom1_atom.is_bonded_to(atom2_atom):
            raise Exception('Bond already exists between {} and {}'.format(
                atom1_atom, atom2_atom))
        bond = Bond(
            atom1_atom,
            atom2_atom,
            bond_order,
            is_aromatic,
            stereochemistry=stereochemistry,
            fractional_bond_order=fractional_bond_order)
        self._bonds.append(bond)
        self._invalidate_cached_properties()
        # TODO: This is a bad way to get bond index
        return self._bonds.index(bond)

    def _add_conformer(self, coordinates):
        """
        Add a conformation of the molecule

        Parameters
        ----------
        coordinates: simtk.unit.Quantity(np.array) with shape (n_atoms, 3) and dimension of distance
            Coordinates of the new conformer, with the first dimension of the array corresponding to the atom index in
            the Molecule's indexing system.

        Returns
        -------
        index: int
            The index of this conformer
        """
        new_conf = unit.Quantity(
            np.zeros((self.n_atoms, 3), np.float), unit.angstrom)
        if not (new_conf.shape == coordinates.shape):
            raise Exception(
                "molecule.add_conformer given input of the wrong shape: "
                "Given {}, expected {}".format(coordinates.shape,
                                               new_conf.shape))

        try:
            new_conf[:] = coordinates
        except AttributeError as e:
            print(e)
            raise Exception(
                'Coordinates passed to Molecule._add_conformer without units. Ensure that coordinates are '
                'of type simtk.units.Quantity')

        if self._conformers is None:
            #TODO should we checking that the exact same conformer is not in the list already?
            self._conformers = []
        self._conformers.append(new_conf)
        return len(self._conformers)

    @property
    def partial_charges(self):
        """
        Returns the partial charges (if present) on the molecule.

        Returns
        -------
        partial_charges : a simtk.unit.Quantity - wrapped numpy array [1 x n_atoms] or None
            The partial charges on this Molecule's atoms. Returns None if no charges have been specified.
        """
        return self._partial_charges

    @partial_charges.setter
    def partial_charges(self, charges):
        """
        Set the atomic partial charges for this molecule.

        Parameters
        ----------
        charges : a simtk.unit.Quantity - wrapped numpy array [1 x n_atoms]
            The partial charges to assign to the molecule. Must be in units compatible with simtk.unit.elementary_charge
        """
        assert hasattr(charges, 'unit')
        assert unit.elementary_charge.is_compatible(charges.unit)
        assert charges.shape == (self.n_atoms, )

        charges_ec = charges.in_units_of(unit.elementary_charge)
        self._partial_charges = charges_ec

    @property
    def n_particles(self):
        """
        The number of Particle objects, which corresponds to how many positions must be used.
        """
        return len(self._atoms) + len(self._virtual_sites)

    @property
    def n_atoms(self):
        """
        The number of Atom objects.
        """
        return len(self._atoms)

    @property
    def n_virtual_sites(self):
        """
        The number of VirtualSite objects.
        """
        return sum([1 for virtual_site in self.virtual_sites])

    @property
    def n_bonds(self):
        """
        The number of Bond objects.
        """
        return sum([1 for bond in self.bonds])

    @property
    def n_angles(self):
        """int: number of angles in the Molecule."""
        self._construct_angles()
        return len(self._angles)

    @property
    def n_propers(self):
        """int: number of proper torsions in the Molecule."""
        self._construct_torsions()
        return len(self._propers)

    @property
    def n_impropers(self):
        """int: number of improper torsions in the Molecule."""
        self._construct_torsions()
        return len(self._impropers)

    @property
    def particles(self):
        """
        Iterate over all Particle objects.
        """
        # TODO: Re-implement this when we see how it interfaces with Topology
        return self._atoms + self._virtual_sites

    @property
    def atoms(self):
        """
        Iterate over all Atom objects.
        """
        return self._atoms

    @property
    def conformers(self):
        """
        Returns the list of conformers for this molecule. This returns a list of simtk.unit.Quantity-wrapped numpy
        arrays, of shape (3 x n_atoms) and with dimensions of distance. The return value is the actual list of
        conformers, and changes to the contents affect the original FrozenMolecule.

        """
        return self._conformers

    @property
    def n_conformers(self):
        """
        Returns the number of conformers for this molecule.
        """
        if self._conformers is None:
            return 0
        return len(self._conformers)

    @property
    def virtual_sites(self):
        """
        Iterate over all VirtualSite objects.
        """
        return self._virtual_sites

    @property
    def bonds(self):
        """
        Iterate over all Bond objects.
        """
        return self._bonds

    @property
    def angles(self):
        """
        Get an iterator over all i-j-k angles.
        """
        self._construct_angles()
        return self._angles

    @property
    def torsions(self):
        """
        Get an iterator over all i-j-k-l torsions.
        Note that i-j-k-i torsions (cycles) are excluded.

        Returns
        -------
        torsions : iterable of 4-Atom tuples
        """
        self._construct_torsions()
        return self._torsions

    @property
    def propers(self):
        """
        Iterate over all proper torsions in the molecule

        .. todo::

           * Do we need to return a ``Torsion`` object that collects information about fractional bond orders?
        """
        self._construct_torsions()
        return self._propers

    @property
    def impropers(self):
        """
        Iterate over all proper torsions in the molecule

        .. todo::

           * Do we need to return a ``Torsion`` object that collects information about fractional bond orders?
        """
        self._construct_torsions()
        return self._impropers

    @property
    def total_charge(self):
        """
        Return the total charge on the molecule
        """
        return sum([atom.formal_charge for atom in self.atoms])

    @property
    def name(self):
        """
        The name (or title) of the molecule
        """
        return self._name

    @name.setter
    def name(self, other):
        """
        Set the name of this molecule
        """
        if other is None:
            self._name = ''
        elif type(other) is str:
            self._name = other
        else:
            raise Exception("Molecule name must be a string")

    @property
    def properties(self):
        """
        The properties dictionary of the molecule
        """
        return self._properties

    @property
    def hill_formula(self):
        """
        Get the Hill formula of the molecule
        """
        return Molecule.to_hill_formula(self)

    @staticmethod
    def to_hill_formula(molecule):
        """
        Generate the Hill formula from either a FrozenMolecule, TopologyMolecule or
        nx.Graph() of the molecule

        Parameters
        -----------
        molecule : FrozenMolecule, TopologyMolecule or nx.Graph()

        Returns
        ----------
        formula : the Hill formula of the molecule

        Raises
        -----------
        NotImplementedError : if the molecule is not of one of the specified types.
        """

        from openforcefield.topology import TopologyMolecule

        # check for networkx then assuming we have a Molecule or TopologyMolecule instance just try and
        # extract the info. Note we do not type check the TopologyMolecule due to cyclic dependencies
        if isinstance(molecule, nx.Graph):
            atom_nums = list(dict(molecule.nodes(data='atomic_number', default=1)).values())

        elif isinstance(molecule, TopologyMolecule):
            atom_nums = [atom.atomic_number for atom in molecule.atoms]

        elif isinstance(molecule, FrozenMolecule):
            atom_nums = [atom.atomic_number for atom in molecule.atoms]

        else:
            raise NotImplementedError(f'The input type {type(molecule)} is not supported,'
                                      f'please supply an openforcefield.topology.molecule.Molecule,'
                                      f'openforcefield.topology.topology.TopologyMolecule or networkx representaion '
                                      f'of the molecule.')

        # make a correct hill formula representation following this guide
        # https://en.wikipedia.org/wiki/Chemical_formula#Hill_system

        # create the counter dictionary using chemical symbols
        atom_symbol_counts = Counter(Element.getByAtomicNumber(atom_num).symbol for atom_num in atom_nums)

        formula = []
        # Check for C and H first, to make a correct hill formula
        for el in ['C', 'H']:
            if el in atom_symbol_counts:
                count = atom_symbol_counts.pop(el)
                formula.append(el)
                if count > 1:
                    formula.append(str(count))

        # now get the rest of the elements in alphabetical ordering
        for el in sorted(atom_symbol_counts.keys()):
            count = atom_symbol_counts.pop(el)
            formula.append(el)
            if count > 1:
                formula.append(str(count))

        return "".join(formula)

    def chemical_environment_matches(self,
                                     query,
                                     toolkit_registry=GLOBAL_TOOLKIT_REGISTRY):
        """Retrieve all matches for a given chemical environment query.

        Parameters
        ----------
        query : str or ChemicalEnvironment
            SMARTS string (with one or more tagged atoms) or ``ChemicalEnvironment`` query
            Query will internally be resolved to SMIRKS using ``query.asSMIRKS()`` if it has an ``.asSMIRKS`` method.
        toolkit_registry : openforcefield.utils.toolkits.ToolkitRegistry or openforcefield.utils.toolkits.ToolkitWrapper, optional, default=GLOBAL_TOOLKIT_REGISTRY
            :class:`ToolkitRegistry` or :class:`ToolkitWrapper` to use for chemical environment matches


        Returns
        -------
        matches : list of atom index tuples
            A list of tuples, containing the indices of the matching atoms.

        Examples
        --------
        Retrieve all the carbon-carbon bond matches in a molecule

        >>> molecule = Molecule.from_iupac('imatinib')
        >>> matches = molecule.chemical_environment_matches('[#6X3:1]~[#6X3:2]')

        .. todo ::

           * Do we want to generalize ``query`` to allow other kinds of queries, such as mdtraj DSL, pymol selections, atom index slices, etc?
             We could call it ``topology.matches(query)`` instead of ``chemical_environment_matches``

        """
        # Resolve to SMIRKS if needed
        # TODO: Update this to use updated ChemicalEnvironment API
        if hasattr(query, 'asSMIRKS'):
            smirks = query.asSMIRKS()
        elif type(query) == str:
            smirks = query
        else:
            raise ValueError(
                "'query' must be either a string or a ChemicalEnvironment")

        # Use specified cheminformatics toolkit to determine matches with specified aromaticity model
        # TODO: Simplify this by requiring a toolkit registry for the molecule?
        # TODO: Do we have to pass along an aromaticity model?
        if isinstance(toolkit_registry, ToolkitRegistry):
            matches = toolkit_registry.call('find_smarts_matches', self,
                                            smirks)
        elif isinstance(toolkit_registry, ToolkitWrapper):
            matches = toolkit_registry.find_smarts_matches(self, smirks)
        else:
            raise ValueError(
                "'toolkit_registry' must be either a ToolkitRegistry or a ToolkitWrapper"
            )

        return matches

    # TODO: Move OE-dependent parts of this to toolkits.py
    @classmethod
    @OpenEyeToolkitWrapper.requires_toolkit()
    def from_iupac(cls, iupac_name, **kwargs):
        """Generate a molecule from IUPAC or common name

        Parameters
        ----------
        iupac_name : str
            IUPAC name of molecule to be generated
        allow_undefined_stereo : bool, default=False
            If false, raises an exception if molecule contains undefined stereochemistry.

        Returns
        -------
        molecule : Molecule
            The resulting molecule with position

        .. note :: This method requires the OpenEye toolkit to be installed.

        Examples
        --------

        Create a molecule from a common name

        >>> molecule = Molecule.from_iupac('4-[(4-methylpiperazin-1-yl)methyl]-N-(4-methyl-3-{[4-(pyridin-3-yl)pyrimidin-2-yl]amino}phenyl)benzamide')

        Create a molecule from a common name

        >>> molecule = Molecule.from_iupac('imatinib')

        """
        from openeye import oechem, oeiupac
        oemol = oechem.OEMol()
        oeiupac.OEParseIUPACName(oemol, iupac_name)
        oechem.OETriposAtomNames(oemol)
        result = oechem.OEAddExplicitHydrogens(oemol)
        if result == False:
            raise Exception(
                "Addition of explicit hydrogens failed in from_iupac")
        molecule = cls.from_openeye(oemol, **kwargs)
        return molecule

    # TODO: Move OE-dependent parts of this to toolkits.py
    @OpenEyeToolkitWrapper.requires_toolkit()
    def to_iupac(self):
        """Generate IUPAC name from Molecule

        Returns
        -------
        iupac_name : str
            IUPAC name of the molecule

        .. note :: This method requires the OpenEye toolkit to be installed.

        Examples
        --------

        >>> from openforcefield.utils import get_data_file_path
        >>> sdf_filepath = get_data_file_path('molecules/ethanol.sdf')
        >>> molecule = Molecule(sdf_filepath)
        >>> iupac_name = molecule.to_iupac()

        """
        from openeye import oeiupac
        return oeiupac.OECreateIUPACName(self.to_openeye())

    @staticmethod
    def from_topology(topology):
        """Return a Molecule representation of an openforcefield Topology containing a single Molecule object.

        Parameters
        ----------
        topology : openforcefield.topology.Topology
            The :class:`Topology` object containing a single :class:`Molecule` object.
            Note that OpenMM and MDTraj ``Topology`` objects are not supported.

        Returns
        -------
        molecule : openforcefield.topology.Molecule
            The Molecule object in the topology

        Raises
        ------
        ValueError
            If the topology does not contain exactly one molecule.

        Examples
        --------

        Create a molecule from a Topology object that contains exactly one molecule

        >>> molecule = Molecule.from_topology(topology)  # doctest: +SKIP

        """
        # TODO: Ensure we are dealing with an openforcefield Topology object
        if topology.n_topology_molecules != 1:
            raise ValueError('Topology must contain exactly one molecule')
        molecule = [i for i in topology.reference_molecules][0]
        return Molecule(molecule)

    def to_topology(self):
        """
        Return an openforcefield Topology representation containing one copy of this molecule

        Returns
        -------
        topology : openforcefield.topology.Topology
            A Topology representation of this molecule

        Examples
        --------

        >>> molecule = Molecule.from_iupac('imatinib')
        >>> topology = molecule.to_topology()

        """
        from openforcefield.topology import Topology
        return Topology.from_molecules(self)

    @staticmethod
    def from_file(file_path,
                  file_format=None,
                  toolkit_registry=GLOBAL_TOOLKIT_REGISTRY,
                  allow_undefined_stereo=False):
        """
        Create one or more molecules from a file

        .. todo::

           * Extend this to also include some form of .offmol Open Force Field Molecule format?
           * Generalize this to also include file-like objects?

        Parameters
        ----------
        file_path : str or file-like object
            The path to the file or file-like object to stream one or more molecules from.
        file_format : str, optional, default=None
            Format specifier, usually file suffix (eg. 'MOL2', 'SMI')
            Note that not all toolkits support all formats. Check ToolkitWrapper.toolkit_file_read_formats for your
            loaded toolkits for details.
        toolkit_registry : openforcefield.utils.toolkits.ToolkitRegistry or openforcefield.utils.toolkits.ToolkitWrapper,
        optional, default=GLOBAL_TOOLKIT_REGISTRY
            :class:`ToolkitRegistry` or :class:`ToolkitWrapper` to use for file loading. If a Toolkit is passed, only
            the highest-precedence toolkit is used
        allow_undefined_stereo : bool, default=False
            If false, raises an exception if oemol contains undefined stereochemistry.

        Returns
        -------
        molecules : Molecule or list of Molecules
            If there is a single molecule in the file, a Molecule is returned;
            otherwise, a list of Molecule objects is returned.

        Examples
        --------
        >>> from openforcefield.tests.utils import get_monomer_mol2_file_path
        >>> mol2_file_path = get_monomer_mol2_file_path('cyclohexane')
        >>> molecule = Molecule.from_file(mol2_file_path)

        """

        if file_format is None:
            if not (isinstance(file_path, str)):
                raise Exception(
                    "If providing a file-like object for reading molecules, the format must be specified"
                )
            # Assume that files ending in ".gz" should use their second-to-last suffix for compatibility check
            # TODO: Will all cheminformatics packages be OK with gzipped files?
            if file_path[-3:] == '.gz':
                file_format = file_path.split('.')[-2]
            else:
                file_format = file_path.split('.')[-1]
        file_format = file_format.upper()

        # Determine which toolkit to use (highest priority that's compatible with input type)
        if isinstance(toolkit_registry, ToolkitRegistry):
            # TODO: Encapsulate this logic into ToolkitRegistry.call()?
            toolkit = None
            supported_read_formats = {}
            for query_toolkit in toolkit_registry.registered_toolkits:
                if file_format in query_toolkit.toolkit_file_read_formats:
                    toolkit = query_toolkit
                    break
                supported_read_formats[
                    query_toolkit.
                    toolkit_name] = query_toolkit.toolkit_file_read_formats
            if toolkit is None:
                msg = f"No toolkits in registry can read file {file_path} (format {file_format}). Supported " \
                      f"formats in the provided ToolkitRegistry are {supported_read_formats}. "
                # Per issue #407, not allowing RDKit to read mol2 has confused a lot of people. Here we add text
                # to the error message that will hopefully reduce this confusion.
                if file_format == 'MOL2' and RDKitToolkitWrapper.is_available():
                    msg += f"RDKit does not fully support input of molecules from mol2 format unless they " \
                           f"have Corina atom types, and this is not common in the simulation community. For this " \
                           f"reason, the Open Force Field Toolkit does not use " \
                           f"RDKit to read .mol2. Consider reading from SDF instead. If you would like to attempt " \
                           f"to use RDKit to read mol2 anyway, you can load the molecule of interest into an RDKit " \
                           f"molecule and use openforcefield.topology.Molecule.from_rdkit, but we do not recommend this."
                elif file_format == 'PDB' and RDKitToolkitWrapper.is_available():
                    msg += "RDKit can not safely read PDBs on their own. Information about bond order and aromaticity " \
                           "is likely to be lost. PDBs can be used along with a valid smiles string with RDKit using " \
                           "the constructor Molecule.from_pdb_and_smiles(file_path, smiles)"
                raise NotImplementedError(msg)

        elif isinstance(toolkit_registry, ToolkitWrapper):
            # TODO: Encapsulate this logic in ToolkitWrapper?
            toolkit = toolkit_registry
            if file_format not in toolkit.toolkit_file_read_formats:
                msg = f"Toolkit {toolkit.toolkit_name} can not read file {file_path} (format {file_format}). Supported " \
                      f"formats for this toolkit are {toolkit.toolkit_file_read_formats}."
                if toolkit.toolkit_name == 'The RDKit' and file_format == 'PDB':
                    msg += "RDKit can however read PDBs with a valid smiles string using the " \
                           "Molecule.from_pdb_and_smiles(file_path, smiles) constructor"
                raise NotImplementedError(msg)
        else:
            raise ValueError(
                "'toolkit_registry' must be either a ToolkitRegistry or a ToolkitWrapper"
            )

        mols = list()

        if isinstance(file_path, str):
            mols = toolkit.from_file(
                file_path,
                file_format=file_format,
                allow_undefined_stereo=allow_undefined_stereo)
        elif hasattr(file_path, 'read'):
            file_obj = file_path
            mols = toolkit.from_file_obj(
                file_obj,
                file_format=file_format,
                allow_undefined_stereo=allow_undefined_stereo)

        if len(mols) == 0:
            raise Exception(
                'Unable to read molecule from file: {}'.format(file_path))
        elif len(mols) == 1:
            return mols[0]

        return mols

    def _to_xyz_file(self, file_path):
        """
        Write the current molecule and its conformers to a multiframe xyz file, if the molecule
        has no current coordinates all atoms will be set to 0,0,0 in keeping with the behaviour of the
        backend toolkits.

        Parameters
        ----------
        file_path : str or file-like object
            A file-like object or the path to the file to be written.
        """

        # If we do not have a conformer make one with all zeros
        if self.n_conformers == 0:
            conformers = [unit.Quantity(np.zeros((self.n_atoms, self.n_atoms), np.float), unit.angstrom)]

        else:
            conformers = self._conformers

        if len(conformers) == 1:
            end = ''
            title = lambda frame: f'{self.name if self.name is not "" else self.hill_formula}{frame}\n'
        else:
            end = 1
            title = lambda frame: f'{self.name if self.name is not "" else self.hill_formula} Frame {frame}\n'

        # check if we have a file path or an open file object
        if isinstance(file_path, str):
            xyz_data = open(file_path, 'w')
        else:
            xyz_data = file_path

        # add the data to the xyz_data list
        for i, geometry in enumerate(conformers, 1):
            xyz_data.write(f'{self.n_atoms}\n'+title(end))
            for j, atom_coords in enumerate(geometry.in_units_of(unit.angstrom)):
                x, y, z = atom_coords._value
                xyz_data.write(f'{self.atoms[j].element.symbol}       {x: .10f}   {y: .10f}   {z: .10f}\n')

            # now we up the frame count
            end = i + 1

        # now close the file
        xyz_data.close()

    def to_file(self,
                file_path,
                file_format,
                toolkit_registry=GLOBAL_TOOLKIT_REGISTRY):
        """Write the current molecule to a file or file-like object

        Parameters
        ----------
        file_path : str or file-like object
            A file-like object or the path to the file to be written.
        file_format : str
            Format specifier, one of ['MOL2', 'MOL2H', 'SDF', 'PDB', 'SMI', 'CAN', 'TDT']
            Note that not all toolkits support all formats
        toolkit_registry : openforcefield.utils.toolkits.ToolkitRegistry or openforcefield.utils.toolkits.ToolkitWrapper,
        optional, default=GLOBAL_TOOLKIT_REGISTRY
            :class:`ToolkitRegistry` or :class:`ToolkitWrapper` to use for file writing. If a Toolkit is passed, only
            the highest-precedence toolkit is used

        Raises
        ------
        ValueError
            If the requested file_format is not supported by one of the installed cheminformatics toolkits

        Examples
        --------

        >>> molecule = Molecule.from_iupac('imatinib')
        >>> molecule.to_file('imatinib.mol2', file_format='mol2')  # doctest: +SKIP
        >>> molecule.to_file('imatinib.sdf', file_format='sdf')  # doctest: +SKIP
        >>> molecule.to_file('imatinib.pdb', file_format='pdb')  # doctest: +SKIP

        """

        if isinstance(toolkit_registry, ToolkitRegistry):
            pass
        elif isinstance(toolkit_registry, ToolkitWrapper):
            toolkit = toolkit_registry
            toolkit_registry = ToolkitRegistry(toolkit_precedence=[])
            toolkit_registry.add_toolkit(toolkit)
        else:
            raise ValueError(
                "'toolkit_registry' must be either a ToolkitRegistry or a ToolkitWrapper"
            )

        file_format = file_format.upper()

        # check if xyz, use the toolkit independent method.
        if file_format == 'XYZ':
            return self._to_xyz_file(file_path=file_path)

        # Take the first toolkit that can write the desired output format
        toolkit = None
        for query_toolkit in toolkit_registry.registered_toolkits:
            if file_format in query_toolkit.toolkit_file_write_formats:
                toolkit = query_toolkit
                break

        # Raise an exception if no toolkit was found to provide the requested file_format
        if toolkit is None:
            supported_formats = {}
            for toolkit in toolkit_registry.registered_toolkits:
                supported_formats[
                    toolkit.toolkit_name] = toolkit.toolkit_file_write_formats
            raise ValueError(
                'The requested file format ({}) is not available from any of the installed toolkits '
                '(supported formats: {})'.format(file_format,
                                                 supported_formats))

        # Write file
        if type(file_path) == str:
            # Open file for writing
            toolkit.to_file(self, file_path, file_format)
        else:
            toolkit.to_file_obj(self, file_path, file_format)

    @staticmethod
    @RDKitToolkitWrapper.requires_toolkit()
    def from_rdkit(rdmol, allow_undefined_stereo=False):
        """
        Create a Molecule from an RDKit molecule.

        Requires the RDKit to be installed.

        Parameters
        ----------
        rdmol : rkit.RDMol
            An RDKit molecule
        allow_undefined_stereo : bool, default=False
            If false, raises an exception if oemol contains undefined stereochemistry.

        Returns
        -------
        molecule : openforcefield.Molecule
            An openforcefield molecule

        Examples
        --------

        Create a molecule from an RDKit molecule

        >>> from rdkit import Chem
        >>> from openforcefield.tests.utils import get_data_file_path
        >>> rdmol = Chem.MolFromMolFile(get_data_file_path('systems/monomers/ethanol.sdf'))
        >>> molecule = Molecule.from_rdkit(rdmol)

        """
        toolkit = RDKitToolkitWrapper()
        molecule = toolkit.from_rdkit(
            rdmol, allow_undefined_stereo=allow_undefined_stereo)
        return molecule

    @RDKitToolkitWrapper.requires_toolkit()
    def to_rdkit(self, aromaticity_model=DEFAULT_AROMATICITY_MODEL):
        """
        Create an RDKit molecule

        Requires the RDKit to be installed.

        Parameters
        ----------
        aromaticity_model : str, optional, default=DEFAULT_AROMATICITY_MODEL
            The aromaticity model to use

        Returns
        -------
        rdmol : rkit.RDMol
            An RDKit molecule

        Examples
        --------

        Convert a molecule to RDKit

        >>> from openforcefield.utils import get_data_file_path
        >>> sdf_filepath = get_data_file_path('molecules/ethanol.sdf')
        >>> molecule = Molecule(sdf_filepath)
        >>> rdmol = molecule.to_rdkit()

        """
        toolkit = RDKitToolkitWrapper()
        return toolkit.to_rdkit(self, aromaticity_model=aromaticity_model)

    @staticmethod
    @OpenEyeToolkitWrapper.requires_toolkit()
    def from_openeye(oemol, allow_undefined_stereo=False):
        """
        Create a Molecule from an OpenEye molecule.

        Requires the OpenEye toolkit to be installed.

        Parameters
        ----------
        oemol : openeye.oechem.OEMol
            An OpenEye molecule
        allow_undefined_stereo : bool, default=False
            If false, raises an exception if oemol contains undefined stereochemistry.

        Returns
        -------
        molecule : openforcefield.topology.Molecule
            An openforcefield molecule

        Examples
        --------

        Create a Molecule from an OpenEye OEMol

        >>> from openeye import oechem
        >>> from openforcefield.tests.utils import get_data_file_path
        >>> ifs = oechem.oemolistream(get_data_file_path('systems/monomers/ethanol.mol2'))
        >>> oemols = list(ifs.GetOEGraphMols())
        >>> molecule = Molecule.from_openeye(oemols[0])

        """
        toolkit = OpenEyeToolkitWrapper()
        molecule = toolkit.from_openeye(
            oemol, allow_undefined_stereo=allow_undefined_stereo)
        return molecule

    def to_qcschema(self, multiplicity=1, conformer=0):
        """
        Generate the qschema input format used to submit jobs to archive
        or run qcengine calculations locally, the molecule is placed in canonical order first.
        spec can be found here <https://molssi-qc-schema.readthedocs.io/en/latest/index.html>

        .. warning :: This API is experimental and subject to change.

        Parameters
        ----------
        multiplicity : int, default=1,
            The multiplicity of the molecule required for qcschema

        conformer : int, default=0,
            The index of the conformer that should be used for qcschema

        Returns
        ---------
        qcelemental.models.Molecule :
            A validated qcschema

        Example
        -------

        Create and validate a qcelemental input

        >>> import qcelemental as qcel
        >>> mol = Molecule.from_smiles('CC')
        >>> mol.generate_conformers(n_conformers=1)
        >>> qcschema = mol.to_qcschema()

        Raises
        --------
        ImportError : if qcelemental is not installed; the qcschema can not be validated.

        InvalidConformerError : if there is no conformer found at the given index.
        """

        try:
            import qcelemental as qcel
        except ImportError:
            raise ImportError('Please install QCElemental via conda install -c conda-forge qcelemental '
                              'to validate the schema')

        # get a canonical ordered version of the molecule
        canonical_mol = self.canonical_order_atoms()

        # get/ check the geometry
        try:
            geometry = canonical_mol.conformers[conformer].in_units_of(unit.bohr)
        except (IndexError, TypeError):
            raise InvalidConformerError('The molecule must have a conformation to produce a valid qcschema; '
                                        f'no conformer was found at index {conformer}.')

        # Gather the required qschema data
        charge = sum([atom.formal_charge for atom in canonical_mol.atoms])
        connectivity = [(bond.atom1_index, bond.atom2_index, bond.bond_order) for bond in canonical_mol.bonds]
        symbols = [Element.getByAtomicNumber(atom.atomic_number).symbol for atom in canonical_mol.atoms]

        schema_dict = {'symbols': symbols, 'geometry': geometry, 'connectivity': connectivity,
                       'molecular_charge': charge, 'molecular_multiplicity': multiplicity}

        return qcel.models.Molecule.from_data(schema_dict, validate=True)

    @classmethod
    def from_mapped_smiles(cls, mapped_smiles, toolkit_registry=GLOBAL_TOOLKIT_REGISTRY, allow_undefined_stereo=False):
        """
        Create an openforcefield.topology.molecule.Molecule from a mapped SMILES made with cmiles.
        The molecule will be in the order of the indexing in the mapped smiles string.

        .. warning :: This API is experimental and subject to change.

        Parameters
        ----------
        mapped_smiles: str,
            A CMILES-style mapped smiles string with explicit hydrogens.

        toolkit_registry : openforcefield.utils.toolkits.ToolkitRegistry or openforcefield.utils.toolkits.ToolkitWrapper, optional, default=None
            :class:`ToolkitRegistry` or :class:`ToolkitWrapper` to use for SMILES-to-molecule conversion

        allow_undefined_stereo : bool, default=False
            If false, raises an exception if oemol contains undefined stereochemistry.

        Returns
        ----------
        offmol : openforcefield.topology.molecule.Molecule
            An openforcefiled molecule instance.

        Raises
        --------
        SmilesParsingError : if the given SMILES had no indexing picked up by the toolkits.
        """

        # create the molecule from the smiles and check we have the right number of indexes
        # in the mapped SMILES
        offmol = cls.from_smiles(mapped_smiles, hydrogens_are_explicit=True, toolkit_registry=toolkit_registry,
                                 allow_undefined_stereo=allow_undefined_stereo)

        # check we found some mapping and remove it as we do not want to expose atom maps
        try:
            mapping = offmol._properties.pop('atom_map')
        except KeyError:
            raise SmilesParsingError('The given SMILES has no indexing, please generate a valid explicit hydrogen '
                                     'mapped SMILES using cmiles.')

        if len(mapping) != offmol.n_atoms:
            raise SmilesParsingError('The mapped smiles does not contain enough indexes to remap the molecule.')

        # remap the molecule using the atom map found in the smiles
        # the order is mapping = Dict[current_index: new_index]
        # first renumber the mapping dict indexed from 0, currently from 1 as 0 indicates no mapping in toolkits
        adjusted_mapping = dict((current, new - 1) for current, new in mapping.items())

        return offmol.remap(adjusted_mapping, current_to_new=True)

    @classmethod
    def from_qcschema(cls, qca_record, client=None, toolkit_registry=GLOBAL_TOOLKIT_REGISTRY, allow_undefined_stereo=False):
        """
        Create a Molecule from  a QCArchive entry based on the cmiles information.

        If we also have a client instance/address we can go and attach the starting geometry.

        Parameters
        ----------
        qca_record : dict,
            A QCArchive dict with json encoding or record instance

        client : optional, default=None,
            A qcportal.FractalClient instance so we can pull the initial molecule geometry.

        toolkit_registry : openforcefield.utils.toolkits.ToolkitRegistry or openforcefield.utils.toolkits.ToolkitWrapper, optional, default=None
            :class:`ToolkitRegistry` or :class:`ToolkitWrapper` to use for SMILES-to-molecule conversion

        allow_undefined_stereo : bool, default=False
            If false, raises an exception if oemol contains undefined stereochemistry.

        Returns
        -------
        molecule : openforcefield.topology.Molecule
            An openforcefield molecule instance.

        Raises
        -------
        AttributeError : if the record dict can not be made from a record instance.
            if a client is passed, because the client could not retrive the initial molecule.

        KeyError : if the dict does not contain the canonical_isomeric_explicit_hydrogen_mapped_smiles.

        InvalidConformerError : silent error, if the conformer could not be attached.
        """

        # We can accept the Dataset entry record or the dict with JSON encoding
        # lets get it all in the dict rep
        if not isinstance(qca_record, dict):
            try:
                qca_record = qca_record.dict(encoding='json')
            except AttributeError:
                raise AttributeError('The object passed could not be converted to a dict with json encoding')

        try:
            mapped_smiles = qca_record['attributes']['canonical_isomeric_explicit_hydrogen_mapped_smiles']
        except KeyError:
            raise KeyError('The record must contain the hydrogen mapped smiles to be safley made from the archive.')

        # make a new molecule that has been reordered to match the cmiles mapping
        offmol = cls.from_mapped_smiles(mapped_smiles, toolkit_registry=toolkit_registry,
                                        allow_undefined_stereo=allow_undefined_stereo)

        if client is not None:
            # try and find the initial molecule conformations and attach them
            # collect the input molecules
            try:
                input_mols = client.query_molecules(id=qca_record['initial_molecules'])
            except KeyError:
                # this must be an optimisation record
                input_mols = client.query_molecules(id=qca_record['initial_molecule'])
            except AttributeError:
                raise AttributeError('The provided client can not query molecules, make sure it is an instance of'
                                     'qcportal.client.FractalClient() with the correct address.')
            initial_ids = {}
            # now for each molecule convert and attach the input geometry
            for molecule in input_mols:
                geometry = unit.Quantity(np.array(molecule.geometry, np.float), unit.bohr)
                try:
                    offmol.add_conformer(geometry.in_units_of(unit.angstrom))
                    initial_ids[molecule.id] = offmol.n_conformers - 1
                except InvalidConformerError:
                    print('Invalid conformer for this molecule, the geometry could not be attached.')
            # attach a dict that has the initial molecule ids and the number of the conformer it is stored in
            offmol._properties['initial_molecules'] = initial_ids

        return offmol

    @classmethod
    @RDKitToolkitWrapper.requires_toolkit()
    def from_pdb_and_smiles(cls, file_path, smiles, allow_undefined_stereo=False):
        """
        Create a Molecule from a pdb file and a SMILES string using RDKit.

        Requires RDKit to be installed.

        .. warning :: This API is experimental and subject to change.

        The molecule is created and sanitised based on the SMILES string, we then find a mapping
        between this molecule and one from the PDB based only on atomic number and connections.
        The SMILES molecule is then reindex to match the PDB, the conformer is attached and the
        molecule returned.

        Parameters
        ----------
        file_path: str
            PDB file path
        smiles : str
            a valid smiles string for the pdb, used for seterochemistry and bond order

        allow_undefined_stereo : bool, default=False
            If false, raises an exception if oemol contains undefined stereochemistry.

        Returns
        --------
        molecule : openforcefield.Molecule
            An OFFMol instance with ordering the same as used in the PDB file.

        Raises
        ------
        InvalidConformerError : if the SMILES and PDB molecules are not isomorphic.
        """

        toolkit = RDKitToolkitWrapper()
        return toolkit.from_pdb_and_smiles(file_path, smiles, allow_undefined_stereo)

    def canonical_order_atoms(self, toolkit_registry=GLOBAL_TOOLKIT_REGISTRY):
        """
        Canonical order the atoms in a copy of the molecule using a toolkit, returns a new copy.

        .. warning :: This API is experimental and subject to change.

        Parameters
        ----------
        hydrogens_last: bool, default True
            If the canonical ordering should rank the hydrogens last.

        toolkit_registry : openforcefield.utils.toolkits.ToolkitRegistry or openforcefield.utils.toolkits.ToolkitWrapper, optional, default=None
            :class:`ToolkitRegistry` or :class:`ToolkitWrapper` to use for SMILES-to-molecule conversion

         Returns
        -------
        molecule : openforcefield.topology.Molecule
            An new openforcefield-style molecule with atoms in the canonical order.
        """

        if isinstance(toolkit_registry, ToolkitRegistry):
            return toolkit_registry.call('canonical_order_atoms',
                                         self)
        elif isinstance(toolkit_registry, ToolkitWrapper):
            toolkit = toolkit_registry
            return toolkit.canonical_order_atoms(self)
        else:
            raise Exception(
                'Invalid toolkit_registry passed to from_smiles. Expected ToolkitRegistry or ToolkitWrapper. Got  {}'
                .format(type(toolkit_registry)))

    def remap(self, mapping_dict, current_to_new=True):
        """
        Remap all of the indexes in the molecule to match the given mapping dict

        .. warning :: This API is experimental and subject to change.

        Parameters
        ----------
        mapping_dict : dict,
            A dictionary of the mapping between in the indexes, this should start from 0.
        current_to_new : bool, default=True
            The dict is {current_index: new_index} if True else {new_index: current_index}

        Returns
        -------
        new_molecule :  openforcefield.topology.molecule.Molecule
            An openforcefield.Molecule instance with all attributes transferred, in the PDB order.
        """

        if self.n_virtual_sites != 0:
            raise NotImplementedError('We can not remap virtual sites yet!')

        # make sure the size of the mapping matches the current molecule
        if len(mapping_dict) != self.n_atoms:
            raise ValueError(f'The number of mapping indices({len(mapping_dict)}) does not match the number of'
                             f'atoms in this molecule({self.n_atoms})')

        # make two mapping dicts we need new to old for atoms
        # and old to new for bonds
        if current_to_new:
            cur_to_new = mapping_dict
            new_to_cur = dict(zip(mapping_dict.values(), mapping_dict.keys()))
        else:
            new_to_cur = mapping_dict
            cur_to_new = dict(zip(mapping_dict.values(), mapping_dict.keys()))

        new_molecule = Molecule()
        new_molecule.name = self.name

        try:
            # add the atoms list
            for i in range(self.n_atoms):
                # get the old atom info
                old_atom = self._atoms[new_to_cur[i]]
                new_molecule.add_atom(**old_atom.to_dict())
        # this is the first time we access the mapping; catch an index error here corresponding to mapping that starts
        # from 0 or higher
        except (KeyError, IndexError):
            raise IndexError(f'The mapping supplied is missing a relation corresponding to atom({i})')

        # add the bonds but with atom indexes in a sorted ascending order
        for bond in self._bonds:
            atoms = sorted([cur_to_new[bond.atom1_index], cur_to_new[bond.atom2_index]])
            bond_dict = bond.to_dict()
            bond_dict['atom1'] = atoms[0]
            bond_dict['atom2'] = atoms[1]
            new_molecule.add_bond(**bond_dict)

        # we can now resort the bonds
        sorted_bonds = sorted(new_molecule.bonds, key=operator.attrgetter('atom1_index', 'atom2_index'))
        new_molecule._bonds = sorted_bonds

        # remap the charges
        new_charges = np.zeros(self.n_atoms)
        for i in range(self.n_atoms):
            new_charges[i] = self.partial_charges[new_to_cur[i]].value_in_unit(unit.elementary_charge)
        new_molecule.partial_charges = new_charges * unit.elementary_charge

        # remap the conformers there can be more than one
        if self.conformers is not None:
            for conformer in self.conformers:
                new_conformer = np.zeros((self.n_atoms, 3))
                for i in range(self.n_atoms):
                    new_conformer[i] = conformer[new_to_cur[i]].value_in_unit(unit.angstrom)
                new_molecule.add_conformer(new_conformer * unit.angstrom)

        # move any properties across
        new_molecule._properties = self._properties

        return new_molecule

    @OpenEyeToolkitWrapper.requires_toolkit()
    def to_openeye(self, aromaticity_model=DEFAULT_AROMATICITY_MODEL):
        """
        Create an OpenEye molecule

        Requires the OpenEye toolkit to be installed.

        .. todo ::

           * Use stored conformer positions instead of an argument.
           * Should the aromaticity model be specified in some other way?

        Parameters
        ----------
        aromaticity_model : str, optional, default=DEFAULT_AROMATICITY_MODEL
            The aromaticity model to use

        Returns
        -------
        oemol : openeye.oechem.OEMol
            An OpenEye molecule

        Examples
        --------

        Create an OpenEye molecule from a Molecule

        >>> molecule = Molecule.from_smiles('CC')
        >>> oemol = molecule.to_openeye()

        """
        toolkit = OpenEyeToolkitWrapper()
        return toolkit.to_openeye(self, aromaticity_model=aromaticity_model)

    def _construct_angles(self):
        """
        Get an iterator over all i-j-k angles.
        """
        # TODO: Build Angle objects instead of tuple of atoms.
        if not hasattr(self, '_angles'):
            self._construct_bonded_atoms_list()
            self._angles = set()
            for atom1 in self._atoms:
                for atom2 in self._bondedAtoms[atom1]:
                    for atom3 in self._bondedAtoms[atom2]:
                        if atom1 == atom3:
                            continue
                        # TODO: Encapsulate this logic into an Angle class.
                        if atom1.molecule_atom_index < atom3.molecule_atom_index:
                            self._angles.add((atom1, atom2, atom3))
                        else:
                            self._angles.add((atom3, atom2, atom1))

    def _construct_torsions(self):
        """
        Construct sets containing the atoms improper and proper torsions
        """
        # TODO: Build Proper/ImproperTorsion objects instead of tuple of atoms.
        if not hasattr(self, '_torsions'):
            self._construct_bonded_atoms_list()

            #self._torsions = set()
            self._propers = set()
            self._impropers = set()
            for atom1 in self._atoms:
                for atom2 in self._bondedAtoms[atom1]:
                    for atom3 in self._bondedAtoms[atom2]:
                        if atom1 == atom3:
                            continue
                        for atom4 in self._bondedAtoms[atom3]:
                            if atom4 == atom2:
                                continue
                            # Exclude i-j-k-i
                            if atom1 == atom4:
                                continue

                            if atom1.molecule_atom_index < atom4.molecule_atom_index:
                                torsion = (atom1, atom2, atom3, atom4)
                            else:
                                torsion = (atom4, atom3, atom2, atom1)

                            self._propers.add(torsion)

                        for atom3i in self._bondedAtoms[atom2]:
                            if atom3i == atom3:
                                continue
                            if atom3i == atom1:
                                continue

                            improper = (atom1, atom2, atom3, atom3i)
                            self._impropers.add(improper)

            self._torsions = self._propers | self._impropers
        #return iter(self._torsions)

    def _construct_bonded_atoms_list(self):
        """
        Construct list of all atoms each atom is bonded to.

        """
        # TODO: Add this to cached_properties
        if not hasattr(self, '_bondedAtoms'):
            #self._atoms = [ atom for atom in self.atoms() ]
            self._bondedAtoms = dict()
            for atom in self._atoms:
                self._bondedAtoms[atom] = set()
            for bond in self._bonds:
                atom1 = self.atoms[bond.atom1_index]
                atom2 = self.atoms[bond.atom2_index]
                self._bondedAtoms[atom1].add(atom2)
                self._bondedAtoms[atom2].add(atom1)

    def _is_bonded(self, atom_index_1, atom_index_2):
        """Return True if atoms are bonded, False if not.

        Parameters
        ----------
        atom_index_1 : int
        atom_index_2 : int
            Atom indices

        Returns
        -------
        is_bonded : bool
            True if atoms are bonded, False otherwise


        """
        self._construct_bonded_atoms_list()
        atom1 = self._atoms[atom_index_1]
        atom2 = self._atoms[atom_index_2]
        return atom2 in self._bondedAtoms[atom1]

    def get_bond_between(self, i, j):
        """Returns the bond between two atoms

        Parameters
        ----------
        i, j : int or Atom
            Atoms or atom indices to check

        Returns
        -------
        bond : Bond
            The bond between i and j.

        """
        if isinstance(i, int) and isinstance(j, int):
            atom_i = self._atoms[i]
            atom_j = self._atoms[j]
        elif isinstance(i, Atom) and isinstance(j, Atom):
            atom_i = i
            atom_j = j
        else:
            raise TypeError(
                "Invalid input passed to is_bonded(). Expected ints or Atoms, "
                "got {} and {}".format(i, j))

        for bond in atom_i.bonds:

            for atom in bond.atoms:

                if atom == atom_i:
                    continue

                if atom == atom_j:
                    return bond

        from openforcefield.topology import NotBondedError
        raise NotBondedError('No bond between atom {} and {}'.format(i, j))


class Molecule(FrozenMolecule):
    """
    Mutable chemical representation of a molecule, such as a small molecule or biopolymer.

    .. todo :: What other API calls would be useful for supporting biopolymers as small molecules? Perhaps iterating over chains and residues?

    Examples
    --------

    Create a molecule from an sdf file

    >>> from openforcefield.utils import get_data_file_path
    >>> sdf_filepath = get_data_file_path('molecules/ethanol.sdf')
    >>> molecule = Molecule(sdf_filepath)

    Convert to OpenEye OEMol object

    >>> oemol = molecule.to_openeye()

    Create a molecule from an OpenEye molecule

    >>> molecule = Molecule.from_openeye(oemol)

    Convert to RDKit Mol object

    >>> rdmol = molecule.to_rdkit()

    Create a molecule from an RDKit molecule

    >>> molecule = Molecule.from_rdkit(rdmol)

    Create a molecule from IUPAC name (requires the OpenEye toolkit)

    >>> molecule = Molecule.from_iupac('imatinib')

    Create a molecule from SMILES

    >>> molecule = Molecule.from_smiles('Cc1ccccc1')

    .. warning :: This API is experimental and subject to change.

    """

    def __init__(self, *args, **kwargs):
        """
        Create a new Molecule object

        Parameters
        ----------
        other : optional, default=None
            If specified, attempt to construct a copy of the Molecule from the specified object.
            This can be any one of the following:

            * a :class:`Molecule` object
            * a file that can be used to construct a :class:`Molecule` object
            * an ``openeye.oechem.OEMol``
            * an ``rdkit.Chem.rdchem.Mol``
            * a serialized :class:`Molecule` object

        Examples
        --------

        Create an empty molecule:

        >>> empty_molecule = Molecule()

        Create a molecule from a file that can be used to construct a molecule,
        using either a filename or file-like object:

        >>> from openforcefield.utils import get_data_file_path
        >>> sdf_filepath = get_data_file_path('molecules/ethanol.sdf')
        >>> molecule = Molecule(sdf_filepath)
        >>> molecule = Molecule(open(sdf_filepath, 'r'), file_format='sdf')

        >>> import gzip
        >>> mol2_gz_filepath = get_data_file_path('molecules/toluene.mol2.gz')
        >>> molecule = Molecule(gzip.GzipFile(mol2_gz_filepath, 'r'), file_format='mol2')

        Create a molecule from another molecule:

        >>> molecule_copy = Molecule(molecule)

        Convert to OpenEye OEMol object

        >>> oemol = molecule.to_openeye()

        Create a molecule from an OpenEye molecule:

        >>> molecule = Molecule(oemol)

        Convert to RDKit Mol object

        >>> rdmol = molecule.to_rdkit()

        Create a molecule from an RDKit molecule:

        >>> molecule = Molecule(rdmol)

        Create a molecule from a serialized molecule object:

        >>> serialized_molecule = molecule.__getstate__()
        >>> molecule_copy = Molecule(serialized_molecule)

        .. todo ::

           * If a filename or file-like object is specified but the file contains more than one molecule, what is the
           proper behavior? Read just the first molecule, or raise an exception if more than one molecule is found?

           * Should we also support SMILES strings or IUPAC names for ``other``?

        """
        #super(self, Molecule).__init__(*args, **kwargs)
        super(Molecule, self).__init__(*args, **kwargs)

    # TODO: Change this to add_atom(Atom) to improve encapsulation and extensibility?
    def add_atom(self,
                 atomic_number,
                 formal_charge,
                 is_aromatic,
                 stereochemistry=None,
                 name=None):
        """
        Add an atom

        Parameters
        ----------
        atomic_number : int
            Atomic number of the atom
        formal_charge : int
            Formal charge of the atom
        is_aromatic : bool
            If True, atom is aromatic; if False, not aromatic
        stereochemistry : str, optional, default=None
            Either 'R' or 'S' for specified stereochemistry, or None if stereochemistry is irrelevant
        name : str, optional, default=None
            An optional name for the atom

        Returns
        -------
        index : int
            The index of the atom in the molecule

        Examples
        --------

        Define a methane molecule

        >>> molecule = Molecule()
        >>> molecule.name = 'methane'
        >>> C = molecule.add_atom(6, 0, False)
        >>> H1 = molecule.add_atom(1, 0, False)
        >>> H2 = molecule.add_atom(1, 0, False)
        >>> H3 = molecule.add_atom(1, 0, False)
        >>> H4 = molecule.add_atom(1, 0, False)
        >>> bond_idx = molecule.add_bond(C, H1, False, 1)
        >>> bond_idx = molecule.add_bond(C, H2, False, 1)
        >>> bond_idx = molecule.add_bond(C, H3, False, 1)
        >>> bond_idx = molecule.add_bond(C, H4, False, 1)

        """
        atom_index = self._add_atom(
            atomic_number,
            formal_charge,
            is_aromatic,
            stereochemistry=stereochemistry,
            name=name)
        return atom_index

    def add_bond_charge_virtual_site(self,
                                     atoms,
                                     distance,
                                     charge_increments=None,
                                     weights=None,
                                     epsilon=None,
                                     sigma=None,
                                     rmin_half=None,
                                     name=''):
        """
        Create a bond charge-type virtual site, in which the location of the charge is specified by the position of two atoms. This supports placement of a virtual site S along a vector between two specified atoms, e.g. to allow for a sigma hole for halogens or similar contexts. With positive values of the distance, the virtual site lies outside the first indexed atom.
        Parameters
        ----------
        atoms : list of openforcefield.topology.molecule.Atom objects or ints of shape [N
            The atoms defining the virtual site's position or their indices
        distance : float

        weights : list of floats of shape [N] or None, optional, default=None
            weights[index] is the weight of particles[index] contributing to the position of the virtual site. Default is None
        charge_increments : list of floats of shape [N], optional, default=None
            The amount of charge to remove from the VirtualSite's atoms and put in the VirtualSite. Indexing in this list should match the ordering in the atoms list. Default is None.
        epsilon : float
            Epsilon term for VdW properties of virtual site. Default is None.
        sigma : float, default=None
            Sigma term for VdW properties of virtual site. Default is None.
        rmin_half : float
            Rmin_half term for VdW properties of virtual site. Default is None.
        name : string or None, default=''
            The name of this virtual site. Default is ''.

        Returns
        -------
        index : int
            The index of the newly-added virtual site in the molecule

        """

        vsite_index = self._add_bond_charge_virtual_site(
            atoms,
            distance,
            weights=weights,
            charge_increments=charge_increments,
            epsilon=epsilon,
            sigma=sigma,
            rmin_half=rmin_half,
            name=name)
        return vsite_index

    def add_monovalent_lone_pair_virtual_site(self, atoms, distance,
                                              out_of_plane_angle,
                                              in_plane_angle, **kwargs):
        """
        Create a bond charge-type virtual site, in which the location of the charge is specified by the position of three atoms.

        TODO : Do "weights" have any meaning here?

        Parameters
        ----------
        atoms : list of three openforcefield.topology.molecule.Atom objects or ints
            The three atoms defining the virtual site's position or their molecule atom indices
        distance : float

        out_of_plane_angle : float

        in_plane_angle : float

        epsilon : float
            Epsilon term for VdW properties of virtual site. Default is None.
        sigma : float, default=None
            Sigma term for VdW properties of virtual site. Default is None.
        rmin_half : float
            Rmin_half term for VdW properties of virtual site. Default is None.
        name : string or None, default=''
            The name of this virtual site. Default is ''.

        Returns
        -------
        index : int
            The index of the newly-added virtual site in the molecule


        """

        #vsite_index = self._add_monovalent_lone_pair_virtual_site(self, atoms, distance, out_of_plane_angle, in_plane_angle, charge_increments=charge_increments, weights=weights, epsilon=epsilon, sigma=sigma, rmin_half=rmin_half, name=name)
        vsite_index = self._add_monovalent_lone_pair_virtual_site(
            atoms, distance, out_of_plane_angle, in_plane_angle, **kwargs)
        return vsite_index

    #def add_divalent_lone_pair_virtual_site(self, atoms, distance, out_of_plane_angle, in_plane_angle, charge_increments=None, weights=None, epsilon=None, sigma=None, rmin_half=None, name=None):
    def add_divalent_lone_pair_virtual_site(self, atoms, distance,
                                            out_of_plane_angle, in_plane_angle,
                                            **kwargs):
        """
        Create a divalent lone pair-type virtual site, in which the location of the charge is specified by the position of three atoms.

        TODO : Do "weights" have any meaning here?

        Parameters
        ----------
        atoms : list of 3 openforcefield.topology.molecule.Atom objects or ints
            The three atoms defining the virtual site's position or their molecule atom indices
        distance : float

        out_of_plane_angle : float

        in_plane_angle : float

        epsilon : float
            Epsilon term for VdW properties of virtual site. Default is None.
        sigma : float, default=None
            Sigma term for VdW properties of virtual site. Default is None.
        rmin_half : float
            Rmin_half term for VdW properties of virtual site. Default is None.
        name : string or None, default=''
            The name of this virtual site. Default is ''.

        Returns
        -------
        index : int
            The index of the newly-added virtual site in the molecule

        """
        #vsite_index = self._add_divalent_lone_pair_virtual_site(self, atoms, distance, out_of_plane_angle, in_plane_angle, charge_increments=charge_increments, weights=weights, epsilon=epsilon, sigma=sigma, rmin_half=rmin_half, name=name)
        vsite_index = self._add_divalent_lone_pair_virtual_site(
            atoms, distance, out_of_plane_angle, in_plane_angle, **kwargs)
        return vsite_index

    def add_trivalent_lone_pair_virtual_site(self, atoms, distance,
                                             out_of_plane_angle,
                                             in_plane_angle, **kwargs):
        """
        Create a trivalent lone pair-type virtual site, in which the location of the charge is specified by the position of four atoms.

        TODO : Do "weights" have any meaning here?

        Parameters
        ----------
        atoms : list of 4 openforcefield.topology.molecule.Atom objects or ints
            The three atoms defining the virtual site's position or their molecule atom indices
        distance : float

        out_of_plane_angle : float

        in_plane_angle : float

        epsilon : float
            Epsilon term for VdW properties of virtual site. Default is None.
        sigma : float, default=None
            Sigma term for VdW properties of virtual site. Default is None.
        rmin_half : float
            Rmin_half term for VdW properties of virtual site. Default is None.
        name : string or None, default=''
            The name of this virtual site. Default is ''.

        Returns
        -------
        index : int
            The index of the newly-added virtual site in the molecule

        """
        vsite_index = self._add_trivalent_lone_pair_virtual_site(
            atoms, distance, out_of_plane_angle, in_plane_angle, **kwargs)
        return vsite_index

    def add_bond(self,
                 atom1,
                 atom2,
                 bond_order,
                 is_aromatic,
                 stereochemistry=None,
                 fractional_bond_order=None):
        """
        Add a bond between two specified atom indices


        Parameters
        ----------
        atom1 : int or openforcefield.topology.molecule.Atom
            Index of first atom
        atom2 : int or openforcefield.topology.molecule.Atom
            Index of second atom
        bond_order : int
            Integral bond order of Kekulized form
        is_aromatic : bool
            True if this bond is aromatic, False otherwise
        stereochemistry : str, optional, default=None
            Either 'E' or 'Z' for specified stereochemistry, or None if stereochemistry is irrelevant
        fractional_bond_order : float, optional, default=None
            The fractional (eg. Wiberg) bond order

        Returns
        -------
        index: int
            Index of the bond in this molecule

"""
        bond_index = self._add_bond(
            atom1,
            atom2,
            bond_order,
            is_aromatic,
            stereochemistry=stereochemistry,
            fractional_bond_order=fractional_bond_order)
        return bond_index

    def add_conformer(self, coordinates):
        """
        Add a conformation of the molecule

        Parameters
        ----------
        coordinates: simtk.unit.Quantity(np.array) with shape (n_atoms, 3) and dimension of distance
            Coordinates of the new conformer, with the first dimension of the array corresponding to the atom index in
            the Molecule's indexing system.

        Returns
        -------
        index: int
            The index of this conformer
        """

        # TODO how can be check that a set of coords and no connections
        #   is a conformation that does not change connectivity?

        return self._add_conformer(coordinates)


class InvalidConformerError(Exception):
    """
    This error is raised when the conformer added to the molecule
    has a different connectivity to that already defined.
    or anyother conformer related issues.
    """
    pass


class SmilesParsingError(Exception):
    """
    This error is rasied when parsing a smiles string results in an error.
    """
    pass
