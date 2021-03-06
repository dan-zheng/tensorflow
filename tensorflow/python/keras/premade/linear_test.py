# Copyright 2019 The TensorFlow Authors. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# ==============================================================================
"""Tests for Keras Premade Linear models."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import numpy as np

from tensorflow.python.eager import backprop
from tensorflow.python.eager import context
from tensorflow.python.framework import constant_op
from tensorflow.python.framework import dtypes
from tensorflow.python.framework import sparse_tensor
from tensorflow.python.framework import test_util
from tensorflow.python.keras import backend
from tensorflow.python.keras import losses
from tensorflow.python.keras.engine import input_layer
from tensorflow.python.keras.engine import training
from tensorflow.python.keras.layers import core
from tensorflow.python.keras.optimizer_v2 import gradient_descent
from tensorflow.python.keras.premade import linear
from tensorflow.python.ops import variables
from tensorflow.python.platform import test


@test_util.run_all_in_graph_and_eager_modes
class LinearModelTest(test.TestCase):

  def test_linear_model_with_single_input(self):
    model = linear.LinearModel()
    inp = np.random.uniform(low=-5, high=5, size=(64, 2))
    output = .3 * inp[:, 0] + .2 * inp[:, 1]
    model.compile('sgd', 'mse', [])
    model.fit(inp, output, epochs=5)
    self.assertTrue(model.built)

  def test_linear_model_with_multi_input(self):
    model = linear.LinearModel()
    input_a = np.random.uniform(low=-5, high=5, size=(64, 1))
    input_b = np.random.uniform(low=-5, high=5, size=(64, 1))
    output = .3 * input_a + .2 * input_b
    model.compile('sgd', 'mse', [])
    model.fit([input_a, input_b], output, epochs=5)

  def test_linear_model_as_layer(self):
    input_a = input_layer.Input(shape=(1,), name='a')
    output_a = linear.LinearModel()(input_a)
    input_b = input_layer.Input(shape=(1,), name='b')
    output_b = core.Dense(units=1)(input_b)
    output = output_a + output_b
    model = training.Model(inputs=[input_a, input_b], outputs=[output])
    input_a_np = np.random.uniform(low=-5, high=5, size=(64, 1))
    input_b_np = np.random.uniform(low=-5, high=5, size=(64, 1))
    output_np = .3 * input_a_np + .2 * input_b_np
    model.compile('sgd', 'mse', [])
    model.fit([input_a_np, input_b_np], output_np, epochs=5)

  def test_linear_model_with_sparse_input(self):
    indices = constant_op.constant([[0, 0], [0, 2], [1, 0], [1, 1]],
                                   dtype=dtypes.int64)
    values = constant_op.constant([.4, .6, .8, .5])
    shape = constant_op.constant([2, 3], dtype=dtypes.int64)
    model = linear.LinearModel()
    inp = sparse_tensor.SparseTensor(indices, values, shape)
    output = model(inp)
    self.evaluate(variables.global_variables_initializer())
    if context.executing_eagerly():
      weights = model.get_weights()
      weights[0] = np.ones((3, 1))
      model.set_weights(weights)
      output = model(inp)
      self.assertAllClose([[1.], [1.3]], self.evaluate(output))

  def test_linear_model_with_sparse_input_and_custom_training(self):
    batch_size = 64
    indices = []
    values = []
    target = np.zeros((batch_size, 1))
    with context.eager_mode():
      for i in range(64):
        rand_int = np.random.randint(3)
        if rand_int == 0:
          indices.append((i, 0))
          val = np.random.uniform(low=-5, high=5)
          values.append(val)
          target[i] = 0.3 * val
        elif rand_int == 1:
          indices.append((i, 1))
          val = np.random.uniform(low=-5, high=5)
          values.append(val)
          target[i] = 0.2 * val
        else:
          indices.append((i, 0))
          indices.append((i, 1))
          val_1 = np.random.uniform(low=-5, high=5)
          val_2 = np.random.uniform(low=-5, high=5)
          values.append(val_1)
          values.append(val_2)
          target[i] = 0.3 * val_1 + 0.2 * val_2

      indices = np.asarray(indices)
      values = np.asarray(values)
      shape = constant_op.constant([batch_size, 2], dtype=dtypes.int64)
      inp = sparse_tensor.SparseTensor(indices, values, shape)
      model = linear.LinearModel(use_bias=False)
      opt = gradient_descent.SGD()
      for _ in range(20):
        with backprop.GradientTape() as t:
          output = model(inp)
          loss = backend.mean(losses.mean_squared_error(target, output))
        grads = t.gradient(loss, model.trainable_variables)
        grads_and_vars = zip(grads, model.trainable_variables)
        opt.apply_gradients(grads_and_vars)


if __name__ == '__main__':
  test.main()
