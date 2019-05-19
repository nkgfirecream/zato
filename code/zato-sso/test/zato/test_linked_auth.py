# -*- coding: utf-8 -*-

"""
Copyright (C) 2019, Zato Source s.r.o. https://zato.io

Licensed under LGPLv3, see LICENSE.txt for terms and conditions.
"""

from __future__ import absolute_import, division, print_function, unicode_literals

# stdlib
from unittest import main

# Zato
from base import BaseTest
from zato.common import SEC_DEF_TYPE

# ################################################################################################################################
# ################################################################################################################################

class LinkedAuthTestCase(BaseTest):

    def test_create(self):

        self.get('/sso/user/linked', {
            'ust': self.ctx.super_user_ust,
            'user_id': 'zusr20d6006gc18n1t0n0qwbs3wrk2'
        })

        self.post('/zato/sso/user/linked', {
            'ust': self.ctx.super_user_ust,
            'user_id': self.ctx.super_user_id,
            'auth_type': SEC_DEF_TYPE.BASIC_AUTH,
            'auth_id': 2,
            'is_active': True,
        })

        self.delete('/zato/sso/user/linked', {
            'ust': self.ctx.super_user_ust,
            'user_id': self.ctx.super_user_id,
            'auth_type': SEC_DEF_TYPE.BASIC_AUTH,
            'auth_id': 2,
        })

# ################################################################################################################################
# ################################################################################################################################

if __name__ == '__main__':
    main()

# ################################################################################################################################
