import sys
import numpy as np
import torch.nn as nn
import torch.nn.functional as F
import torch
from numpy.linalg import svd
from numpy.random import normal
from math import sqrt
from skimage import io


class UNet(nn.Module):
    def __init__(self,colordim =3):
        super(UNet, self).__init__()
        self.conv1_1 = nn.Conv2d(colordim, 64, 3)  # input of (n,n,1), output of (n-2,n-2,64)
        self.conv1_2 = nn.Conv2d(64, 64, 3, padding = 1)
        self.bn1 = nn.BatchNorm2d(64)
        self.conv2_1 = nn.Conv2d(64, 128, 3, padding = 1)
        self.conv2_2 = nn.Conv2d(128, 128, 3, padding = 1)
        self.bn2 = nn.BatchNorm2d(128)
        self.conv3_1 = nn.Conv2d(128, 256, 3, padding = 1)
        self.conv3_2 = nn.Conv2d(256, 256, 3, padding = 1)
        self.bn3 = nn.BatchNorm2d(256)
        self.conv4_1 = nn.Conv2d(256, 512, 3, padding = 1)
        self.conv4_2 = nn.Conv2d(512, 512, 3, padding = 1)
        self.bn4 = nn.BatchNorm2d(512)
        self.conv5_1 = nn.Conv2d(512, 1024, 3, padding = 1)
        self.conv5_2 = nn.Conv2d(1024, 1024, 3, padding = 1)
        self.upconv5 = nn.Conv2d(1024, 512, 1)
        self.bn5 = nn.BatchNorm2d(512)
        self.bn5_out = nn.BatchNorm2d(1024)
        self.conv6_1 = nn.Conv2d(1024, 512, 3, padding = 1)
        self.conv6_2 = nn.Conv2d(512, 512, 3, padding = 1)
        self.upconv6 = nn.Conv2d(512, 256, 1)
        self.bn6 = nn.BatchNorm2d(256)
        self.bn6_out = nn.BatchNorm2d(512)
        self.conv7_1 = nn.Conv2d(512, 256, 3, padding = 1)
        self.conv7_2 = nn.Conv2d(256, 256, 3, padding = 1)
        self.upconv7 = nn.Conv2d(256, 128, 1)
        self.bn7 = nn.BatchNorm2d(128)
        self.bn7_out = nn.BatchNorm2d(256)
        self.conv8_1 = nn.Conv2d(256, 128, 3, padding = 1)
        self.conv8_2 = nn.Conv2d(128, 128, 3, padding = 1)
        self.upconv8 = nn.Conv2d(128, 64, 1)
        self.bn8 = nn.BatchNorm2d(64)
        self.bn8_out = nn.BatchNorm2d(128)
        self.conv9_1 = nn.Conv2d(128, 64, 3, padding = 1)
        self.conv9_2 = nn.Conv2d(64, 64, 3, padding = 1)
        self.conv9_3 = nn.Conv2d(64, 1, 1)
        self.bn9 = nn.BatchNorm2d(1)
        self.maxpool = nn.MaxPool2d(2, stride=2, return_indices=False, ceil_mode=False)
        self.upsample = nn.UpsamplingBilinear2d(scale_factor=2)
        self._initialize_weights()

    def forward(self, x1):
        x1 = F.relu(self.bn1(self.conv1_2(F.relu(self.conv1_1(x1)))))
        # print('x1 size: %d'%(x1.size(2)))
        x2 = F.relu(self.bn2(self.conv2_2(F.relu(self.conv2_1(self.maxpool(x1))))))
        # print('x2 size: %d'%(x2.size(2)))
        x3 = F.relu(self.bn3(self.conv3_2(F.relu(self.conv3_1(self.maxpool(x2))))))
        # print('x3 size: %d'%(x3.size(2)))
        x4 = F.relu(self.bn4(self.conv4_2(F.relu(self.conv4_1(self.maxpool(x3))))))
        # print('x4 size: %d'%(x4.size(2)))
        xup = F.relu(self.conv5_2(F.relu(self.conv5_1(self.maxpool(x4)))))  # x5
        # print('x5 size: %d'%(xup.size(2)))

        xup = self.bn5(self.upconv5(self.upsample(xup)))  # x6in
        cropidx = (x4.size(2) - xup.size(2)) // 2
        x4 = x4[:, :, cropidx:cropidx + xup.size(2), cropidx:cropidx + xup.size(2)]
        # print('crop1 size: %d, x9 size: %d'%(x4crop.size(2),xup.size(2)))
        xup = self.bn5_out(torch.cat((x4, xup), 1))  # x6 cat x4
        xup = F.relu(self.conv6_2(F.relu(self.conv6_1(xup))))  # x6out

        xup = self.bn6(self.upconv6(self.upsample(xup)))  # x7in
        cropidx = (x3.size(2) - xup.size(2)) // 2
        x3 = x3[:, :, cropidx:cropidx + xup.size(2), cropidx:cropidx + xup.size(2)]
        # print('crop1 size: %d, x9 size: %d'%(x3crop.size(2),xup.size(2)))
        xup = self.bn6_out(torch.cat((x3, xup), 1) ) # x7 cat x3
        xup = F.relu(self.conv7_2(F.relu(self.conv7_1(xup))))  # x7out
        xup = self.bn7(self.upconv7(self.upsample(xup)) ) # x8in
        cropidx = (x2.size(2) - xup.size(2)) // 2
        x2 = x2[:, :, cropidx:cropidx + xup.size(2), cropidx:cropidx + xup.size(2)]
        # print('crop1 size: %d, x9 size: %d'%(x2crop.size(2),xup.size(2)))
        xup = self.bn7_out(torch.cat((x2, xup), 1))  # x8 cat x2
        xup = F.relu(self.conv8_2(F.relu(self.conv8_1(xup))))  # x8out

        xup = self.bn8(self.upconv8(self.upsample(xup)) ) # x9in
        cropidx = (x1.size(2) - xup.size(2)) // 2
        x1 = x1[:, :, cropidx:cropidx + xup.size(2), cropidx:cropidx + xup.size(2)]
        # print('crop1 size: %d, x9 size: %d'%(x1crop.size(2),xup.size(2)))
        xup = self.bn8_out(torch.cat((x1, xup), 1))  # x9 cat x1
        xup = F.relu(self.conv9_3(F.relu(self.conv9_2(F.relu(self.conv9_1(xup))))))  # x9out
        xup = self.bn9(xup)

        return F.sigmoid(self.bn9(xup))

    def _initialize_weights(self):
        for m in self.modules():
            if isinstance(m, nn.Conv2d):
                n = m.kernel_size[0] * m.kernel_size[1] * m.out_channels
                m.weight.data.normal_(0, sqrt(2. / n))
                if m.bias is not None:
                    m.bias.data.zero_()
            elif isinstance(m, nn.BatchNorm2d):
                m.weight.data.fill_(1)
                m.bias.data.zero_()


class UNET():
    def __init__(self, model_path = 'unet_state_dict.pkl'):
        self.model_path = model_path
        self.model = UNet()
        self.model.load_state_dict(torch.load(model_path, map_location = 'cpu'))
        self.zero = torch.tensor(0)
        self.one = torch.tensor(1)

    def predict(self, np_arr):
        data = self._process_arr(np_arr)
        out = self.model(data)
        out = torch.where(out < 0.5, self.zero, self.one)
        out = out.numpy()
        out = out.reshape(464, 464)

        return out

    def _process_arr(self, image):
        image = image[:, 80: 560, :]
        image = image / np.max(image)

        tensor = torch.empty(1, 3, 480, 480)
        for i in range(3):
            tensor[0, i, :, :] = torch.tensor(image[:, :, i])

        return tensor

if __name__ == '__main__':
    image = io.imread(sys.argv[1])
    net = UNET()
    out = net.predict(image)
    io.imshow(out* 255)
    io.show()
