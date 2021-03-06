# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.
import numpy as np
import tvm
import topi
import topi.testing
from topi import util


def test_util():
    x = tvm.const(100, "int32")
    assert util.get_const_int(x) == 100
    assert util.get_const_tuple((x, x)) == (100, 100)


def test_ewise():
    m = tvm.var('m')
    l = tvm.var('l')
    A = tvm.placeholder((m, l), name='A')

    shape = (20, 3)

    def test_apply(func, name, f_numpy, low, high, check_round=False, skip_name_check=False):
        B = func(A)
        assert tuple(B.shape) == tuple(A.shape)
        if not skip_name_check:
            assert B.op.body[0].name == name
        a_np = np.random.uniform(low=low, high=high, size=shape).astype(A.dtype) * 10
        # avoid round check too close to boundary
        if check_round:
            a_np += ((np.fmod(a_np, 1) - 0.5) < 1e-6) * 1e-5
        b_np = f_numpy(a_np)

        def check_device(device):
            ctx = tvm.context(device, 0)
            if not ctx.exist:
                print("Skip because %s is not enabled" % device)
                return
            print("Running on target: %s" % device)
            with tvm.target.create(device):
                s = topi.generic.schedule_injective(B)
            foo = tvm.build(s, [A, B], device, name=name)
            a = tvm.nd.array(a_np, ctx)
            b = tvm.nd.array(np.zeros_like(b_np), ctx)
            foo(a, b)
            tvm.testing.assert_allclose(b.asnumpy(), b_np, rtol=1e-5, atol=1e-5)

        for device in ['cuda', 'opencl', 'metal', 'rocm', 'vulkan', 'llvm', 'nvptx', 'sdaccel',
                       'aocl_sw_emu']:
            check_device(device)


    test_apply(topi.floor, "floor", np.floor, -100, 100)
    test_apply(topi.ceil, "ceil", np.ceil, -100, 100)
    test_apply(topi.sign, "sign", np.sign, -100, 100, skip_name_check=True)
    test_apply(topi.trunc, "trunc", np.trunc, -100, 100)
    test_apply(topi.abs, "fabs", np.abs, -100, 100)
    test_apply(topi.round, "round", np.round, -100, 100, check_round=True)
    test_apply(topi.exp, "exp", np.exp, -1, 1)
    test_apply(topi.tanh, "tanh", np.tanh, -10, 10)
    test_apply(topi.sigmoid, "sigmoid", lambda x:1/(1+np.exp(-x)), -1, 1)
    test_apply(topi.log, "log", np.log, 0, 100)
    test_apply(topi.sqrt, "sqrt", np.sqrt, 0, 100)
    test_apply(topi.rsqrt, "rsqrt", lambda x:np.ones_like(x)/np.sqrt(x), 0, 100, skip_name_check=True)

if __name__ == "__main__":
    test_util()
    test_ewise()
