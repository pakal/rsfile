
Rsopen() Factory
==================

.. module:: rsfile
    :noindex:

``rsopen()`` accepts the same file path kinds as the stdlib :func:`open`: :class:`str`,
:class:`bytes`, and :class:`os.PathLike` objects such as :class:`pathlib.Path`.

Example::

    from pathlib import Path
    from rsfile import rsopen

    with rsopen(Path("example.txt"), "w") as stream:
        stream.write("hello")

.. autofunction:: rsopen





