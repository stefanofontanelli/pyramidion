# Copyright (C) 2012 the Pyramidion authors and contributors
# <see AUTHORS file>
#
# This module is part of Pyramidion and is released under
# the MIT License: http://www.opensource.org/licenses/mit-license.php

def setup_routing(config, prefix, classes, adapter):

    for cls in classes:
        setattr(config.registry,
                '{}_adapter'.format(cls.__name__.lower()),
                setup_adapter(cls, config, prefix, adapter))


def setup_adapter(cls, config, prefix, adapter):
    adapter = adapter(cls=cls)
    adapter.setup_routing(config, prefix)
    return adapter
