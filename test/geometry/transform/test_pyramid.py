import pytest
import torch
from torch.autograd import gradcheck

import kornia
import kornia.testing as utils  # test utils
from kornia.testing import assert_close


class TestPyrUp:
    def test_shape(self, device, dtype):
        inp = torch.zeros(1, 2, 4, 4, device=device, dtype=dtype)
        pyr = kornia.geometry.PyrUp()
        assert pyr(inp).shape == (1, 2, 8, 8)

    def test_shape_batch(self, device, dtype):
        inp = torch.zeros(2, 2, 4, 4, device=device, dtype=dtype)
        pyr = kornia.geometry.PyrUp()
        assert pyr(inp).shape == (2, 2, 8, 8)

    def test_gradcheck(self, device, dtype):
        img = torch.rand(1, 2, 5, 4, device=device, dtype=dtype)
        img = utils.tensor_to_gradcheck_var(img)  # to var
        assert gradcheck(kornia.geometry.pyrup, (img,), nondet_tol=1e-8, raise_exception=True, fast_mode=True)

    def test_jit(self, device, dtype):
        img = torch.rand(2, 3, 4, 5, device=device, dtype=dtype)
        op = kornia.geometry.pyrup
        op_jit = torch.jit.script(op)
        assert_close(op(img), op_jit(img))


class TestPyrDown:
    def test_shape(self, device, dtype):
        inp = torch.zeros(1, 2, 4, 4, device=device, dtype=dtype)
        pyr = kornia.geometry.PyrDown()
        assert pyr(inp).shape == (1, 2, 2, 2)

    def test_shape_custom_factor(self, device, dtype):
        inp = torch.zeros(1, 2, 9, 9, device=device, dtype=dtype)
        pyr = kornia.geometry.PyrDown(factor=3.0)
        assert pyr(inp).shape == (1, 2, 3, 3)

    def test_shape_batch(self, device, dtype):
        inp = torch.zeros(2, 2, 4, 4, device=device, dtype=dtype)
        pyr = kornia.geometry.PyrDown()
        assert pyr(inp).shape == (2, 2, 2, 2)

    def test_symmetry_preserving(self, device, dtype):
        inp = torch.zeros(1, 1, 6, 6, device=device, dtype=dtype)
        inp[:, :, 2:4, 2:4] = 1.0
        pyr_out = kornia.geometry.PyrDown()(inp).squeeze()
        assert_close(pyr_out, pyr_out.flip(0))
        assert_close(pyr_out, pyr_out.flip(1))

    def test_gradcheck(self, device, dtype):
        img = torch.rand(1, 2, 5, 4, device=device, dtype=dtype)
        img = utils.tensor_to_gradcheck_var(img)  # to var
        assert gradcheck(kornia.geometry.pyrdown, (img,), nondet_tol=1e-8, raise_exception=True, fast_mode=True)

    def test_jit(self, device, dtype):
        img = torch.rand(2, 3, 4, 5, device=device, dtype=dtype)
        op = kornia.geometry.pyrdown
        op_jit = torch.jit.script(op)
        assert_close(op(img), op_jit(img))


class TestScalePyramid:
    def test_shape_tuple(self, device, dtype):
        inp = torch.zeros(3, 2, 41, 41, device=device, dtype=dtype)
        SP = kornia.geometry.ScalePyramid(n_levels=1, min_size=30)
        out = SP(inp)
        assert len(out) == 3
        assert len(out[0]) == 1
        assert len(out[1]) == 1
        assert len(out[2]) == 1

    def test_shape_batch(self, device, dtype):
        inp = torch.zeros(3, 2, 31, 31, device=device, dtype=dtype)
        SP = kornia.geometry.ScalePyramid(n_levels=1)
        sp, _, _ = SP(inp)
        assert sp[0].shape == (3, 2, 3 + 1, 31, 31)

    def test_shape_batch_double(self, device, dtype):
        inp = torch.zeros(3, 2, 31, 31, device=device, dtype=dtype)
        SP = kornia.geometry.ScalePyramid(n_levels=1, double_image=True)
        sp, _, _ = SP(inp)
        assert sp[0].shape == (3, 2, 1 + 3, 62, 62)

    def test_n_levels_shape(self, device, dtype):
        inp = torch.zeros(1, 1, 32, 32, device=device, dtype=dtype)
        SP = kornia.geometry.ScalePyramid(n_levels=3)
        sp, _, _ = SP(inp)
        assert sp[0].shape == (1, 1, 3 + 3, 32, 32)

    def test_blur_order(self, device, dtype):
        inp = torch.rand(1, 1, 31, 31, device=device, dtype=dtype)
        SP = kornia.geometry.ScalePyramid(n_levels=3)
        sp, _, _ = SP(inp)
        for _, pyr_level in enumerate(sp):
            for _, img in enumerate(pyr_level):
                img = img.squeeze().view(3, -1)
                max_per_blur_level_val, _ = img.max(dim=1)
                assert torch.argmax(max_per_blur_level_val).item() == 0

    def test_symmetry_preserving(self, device, dtype):
        PS = 16
        R = 2
        inp = torch.zeros(1, 1, PS, PS, device=device, dtype=dtype)
        inp[..., PS // 2 - R : PS // 2 + R, PS // 2 - R : PS // 2 + R] = 1.0
        SP = kornia.geometry.ScalePyramid(n_levels=3)
        sp, _, _ = SP(inp)
        for _, pyr_level in enumerate(sp):
            for _, img in enumerate(pyr_level):
                img = img.squeeze()
                assert_close(img, img.flip(1))
                assert_close(img, img.flip(2))

    def test_gradcheck(self, device, dtype):
        img = torch.rand(1, 2, 7, 9, device=device, dtype=dtype)
        img = utils.tensor_to_gradcheck_var(img)  # to var
        from kornia.geometry import ScalePyramid as SP

        def sp_tuple(img):
            sp, _, _ = SP()(img)
            return tuple(sp)

        assert gradcheck(sp_tuple, (img,), raise_exception=True, nondet_tol=1e-4, fast_mode=True)


class TestBuildPyramid:
    def test_smoke(self, device, dtype):
        input = torch.ones(1, 2, 4, 5, device=device, dtype=dtype)
        pyramid = kornia.geometry.transform.build_pyramid(input, max_level=1)
        assert len(pyramid) == 1
        assert pyramid[0].shape == (1, 2, 4, 5)

    @pytest.mark.parametrize("batch_size", (1, 2, 3))
    @pytest.mark.parametrize("channels", (1, 3))
    @pytest.mark.parametrize("max_level", (2, 3, 4))
    def test_num_levels(self, batch_size, channels, max_level, device, dtype):
        height, width = 16, 20
        input = torch.rand(batch_size, channels, height, width, device=device, dtype=dtype)
        pyramid = kornia.geometry.transform.build_pyramid(input, max_level)
        assert len(pyramid) == max_level
        for i in range(1, max_level):
            img = pyramid[i]
            denom = 2**i
            expected_shape = (batch_size, channels, height // denom, width // denom)
            assert img.shape == expected_shape

    def test_gradcheck(self, device, dtype):
        max_level = 1
        batch_size, channels, height, width = 1, 2, 7, 9
        img = torch.rand(batch_size, channels, height, width, device=device, dtype=dtype)
        img = utils.tensor_to_gradcheck_var(img)  # to var
        assert gradcheck(
            kornia.geometry.transform.build_pyramid, (img, max_level), raise_exception=True, fast_mode=True
        )


class TestBuildLaplacianPyramid:
    def test_smoke(self, device, dtype):
        input = torch.ones(1, 2, 4, 5, device=device, dtype=dtype)
        pyramid = kornia.geometry.transform.build_laplacian_pyramid(input, max_level=1)
        assert len(pyramid) == 1
        assert pyramid[0].shape == (1, 2, 4, 5)

    @pytest.mark.parametrize("batch_size", (1, 2, 3))
    @pytest.mark.parametrize("channels", (1, 3))
    @pytest.mark.parametrize("max_level", (2, 3, 4))
    def test_num_levels(self, batch_size, channels, max_level, device, dtype):
        height, width = 16, 32
        input = torch.rand(batch_size, channels, height, width, device=device, dtype=dtype)
        pyramid = kornia.geometry.transform.build_laplacian_pyramid(input, max_level)
        assert len(pyramid) == max_level
        for i in range(1, max_level):
            img = pyramid[i]
            denom = 2**i
            expected_shape = (batch_size, channels, height // denom, width // denom)
            assert img.shape == expected_shape

    def test_gradcheck(self, device, dtype):
        max_level = 1
        batch_size, channels, height, width = 1, 2, 7, 9
        img = torch.rand(batch_size, channels, height, width, device=device, dtype=dtype)
        img = utils.tensor_to_gradcheck_var(img)  # to var
        assert gradcheck(
            kornia.geometry.transform.build_laplacian_pyramid,
            (img, max_level),
            nondet_tol=1e-8,
            raise_exception=True,
            fast_mode=True,
        )
