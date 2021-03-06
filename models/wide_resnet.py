
"""
    WideResNet model definition
    (originally) ported from https://github.com/meliketoy/wide-resnet.pytorch/blob/master/networks/wide_resnet.py
    ported from https://github.com/izmailovpavel/contrib_swa_examples/blob/master/models/wide_resnet.py
"""

import torchvision.transforms as transforms
import torch.nn as nn
import torch.nn.init as init
import torch.nn.functional as F
import math

__all__ = ['wide_resnet28_10', 'wide_resnet28_12', 'wide_leaky_resnet28_10']


def conv3x3(in_planes, out_planes, stride=1):
    return nn.Conv2d(in_planes, out_planes, kernel_size=3, stride=stride, padding=1, bias=True)


def conv_init(m):
    classname = m.__class__.__name__
    if classname.find('Conv') != -1:
        init.kaiming_normal_(m.weight)
        init.constant_(m.bias, 0)
    elif classname.find('BatchNorm') != -1:
        init.constant_(m.weight, 1)
        init.constant_(m.bias, 0)

def conv_leak_init(m):
    classname = m.__class__.__name__
    if classname.find('Conv') != -1:
        init.kaiming_normal_(m.weight, a=0.2)
        init.constant_(m.bias, 0)
    elif classname.find('BatchNorm') != -1:
        init.constant_(m.weight, 1)
        init.constant_(m.bias, 0)

class WideBasic(nn.Module):
    def __init__(self, in_planes, planes, dropout_rate, stride=1, leak=False):
        super(WideBasic, self).__init__()
        self.leak = leak
        self.bn1 = nn.BatchNorm2d(in_planes)
        self.conv1 = nn.Conv2d(in_planes, planes, kernel_size=3, padding=1, bias=True)
        self.dropout = nn.Dropout(p=dropout_rate)
        self.bn2 = nn.BatchNorm2d(planes)
        self.conv2 = nn.Conv2d(planes, planes, kernel_size=3, stride=stride, padding=1, bias=True)

        self.shortcut = nn.Sequential()
        if stride != 1 or in_planes != planes:
            self.shortcut = nn.Sequential(
                nn.Conv2d(in_planes, planes, kernel_size=1, stride=stride, bias=True),
            )

    def forward(self, x):
        if self.leak:
            out = self.dropout(self.conv1(F.leaky_relu(self.bn1(x), negative_slope=0.2)))
            out = self.conv2(F.leaky_relu(self.bn2(out), negative_slope=0.2))
        else:
            out = self.dropout(self.conv1(F.relu(self.bn1(x))))
            out = self.conv2(F.relu(self.bn2(out)))
        out += self.shortcut(x)

        return out


class WideResNet(nn.Module):
    def __init__(self, num_classes=10, depth=28, widen_factor=10, dropout_rate=0., leak=False):
        super(WideResNet, self).__init__()
        self.in_planes = 16
        self.leak = leak

        assert ((depth - 4) % 6 == 0), 'Wide-resnet depth should be 6n+4'
        n = (depth - 4) / 6
        k = widen_factor

        nstages = [16, 16 * k, 32 * k, 64 * k]

        self.conv1 = conv3x3(3, nstages[0])
        self.layer1 = self._wide_layer(WideBasic, nstages[1], n, dropout_rate, stride=1, leak=self.leak)
        self.layer2 = self._wide_layer(WideBasic, nstages[2], n, dropout_rate, stride=2, leak=self.leak)
        self.layer3 = self._wide_layer(WideBasic, nstages[3], n, dropout_rate, stride=2, leak=self.leak)
        self.bn1 = nn.BatchNorm2d(nstages[3], momentum=0.9)
        self.linear = nn.Linear(nstages[3], num_classes)

    def _wide_layer(self, block, planes, num_blocks, dropout_rate, stride, leak):
        strides = [stride] + [1] * int(num_blocks - 1)
        layers = []

        for stride in strides:
            layers.append(block(self.in_planes, planes, dropout_rate, stride, leak))
            self.in_planes = planes

        return nn.Sequential(*layers)

    def forward(self, x):
        out = self.conv1(x)
        out = self.layer1(out)
        out = self.layer2(out)
        out = self.layer3(out)
        if self.leak:
            out = F.leaky_relu(self.bn1(out), negative_slope=0.2)
        else:
            out = F.relu(self.bn1(out))
        out = F.avg_pool2d(out, out.size(3))
        out = out.view(out.size(0), -1)
        out = self.linear(out)
        return out


def wide_resnet28_10(pretrained=None, progress=None, small_inputs=None, **kwargs):
    """Constructs a Wide ResNet-28-10 model.
    Args:
        pretrained (bool): Empty variable for common interface
        progress (bool): Empty variable for common interface
        small_inputs: Unused
    """
    net = WideResNet(**kwargs, depth=28, widen_factor=10)
    net.apply(conv_init)
    return net


def wide_leaky_resnet28_10(pretrained=None, progress=None, small_inputs=None, **kwargs):
    """Constructs a Wide ResNet-28-10 model.
    Args:
        pretrained (bool): Empty variable for common interface
        progress (bool): Empty variable for common interface
        small_inputs: Unused
    """
    net = WideResNet(**kwargs, depth=28, widen_factor=10, leak=True)
    net.apply(conv_leak_init)
    return net


def wide_resnet28_12(pretrained=None, progress=None, small_inputs=None, **kwargs):
    """Constructs a Wide ResNet-28-10 model.
    Args:
        pretrained (bool): Empty variable for common interface
        progress (bool): Empty variable for common interface
        small_inputs: Unused
    """
    net = WideResNet(**kwargs, depth=28, widen_factor=12)
    net.apply(conv_init)
    return net


def wide_resnet40_2(pretrained=None, progress=None, small_inputs=None, **kwargs):
    """Constructs a Wide ResNet-28-10 model.
    Args:
        pretrained (bool): Empty variable for common interface
        progress (bool): Empty variable for common interface
        small_inputs: Unused
    """

    net = WideResNet(**kwargs, depth=40, widen_factor=2)
    net.apply(conv_init)
    return net

def obtain_wide_resnet(model_name = 'wide_resnet28_10', num_classes=100, dropout_rate=0):
    if model_name == 'wide_resnet28_10':
        return wide_resnet28_10(num_classes=num_classes, dropout_rate=dropout_rate)
    elif model_name == 'wide_resnet28_12':
        return wide_resnet28_12(num_classes=num_classes, dropout_rate=dropout_rate)
    elif model_name == 'wide_resnet40_2':
        return wide_resnet40_2(num_classes=num_classes, dropout_rate=dropout_rate)
