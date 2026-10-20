"""NextGen POS - a point-of-sale system built with object-oriented techniques.

Layered logical architecture (see ``docs/diagrams/package-diagram``):

======================  ==================================================
Layer                   Responsibility
======================  ==================================================
``presentation``        Tkinter windows and widgets; UI events only
``application``         One controller per use case; coordinates the work
``domain``              Conceptual classes with the business logic
``technical``           Gateways/adapters, repositories, audit log, seed data
======================  ==================================================

The dependency rule is the one the book recommends: **higher layers depend on
lower layers, never the reverse.**  ``domain`` imports nothing from
``presentation``, ``application`` or ``technical``.
"""
__version__ = "1.0.0"
__all__ = ["__version__"]
