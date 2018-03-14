# -*- coding: utf-8 -*-
#

# Imports
from torch.utils.data.dataset import Dataset
import urllib
import os
import zipfile
import codecs
from lxml import etree
import json
import codecs
from PIL import Image
import torch
import matplotlib.pyplot as plt


# Author profiling data set
class AuthorProfilingDataset(Dataset):
    """
    Author profiling dataset
    """

    # Constructor
    def __init__(self, min_length, root='./data', download=True, lang='en', text_transform=None, image_transform=None, image_size=600):
        """
        Constructor
        :param min_length: Add zero to reach minimum length
        :param root:
        :param download:
        :param lang:
        :param text_transform:
        :param image_transform:
        """
        # Properties
        self.min_length = min_length
        self.root = root
        self.lang = lang
        self.text_transform = text_transform
        self.image_transform = image_transform
        self.downloaded = False
        self.classes = {'female': 0, 'male': 1}
        self.image_size = image_size

        # List of author's IDs
        self.idxs = list()

        # Create directory
        if not os.path.exists(self.root):
            self._create_root()
        # end if

        # Scan root
        for file_name in os.listdir(self.root):
            if u".xml" in file_name:
                self.downloaded = True
                break
            # end if
        # end for

        # Download the data set
        if download and not self.downloaded:
            self._download()
        # end if

        # Load labels
        self.labels = self._load_labels()

        # Load idxs
        self._load()
    # end __init__

    ##############################################
    # OVERRIDE
    ##############################################

    # Length
    def __len__(self):
        """
        Length
        :return:
        """
        return len(self.idxs)
    # end __len__

    # Get item
    def __getitem__(self, item):
        """
        Get item
        :param item:
        :return:
        """
        # Current IDXS
        current_idxs = self.idxs[item]

        # Path to file
        path_to_file = os.path.join(self.root, current_idxs + ".xml")

        # Load  XML
        tree = etree.parse(path_to_file)

        # Texts and images
        tweets = torch.Tensor()
        images = torch.Tensor()

        # Get each documents
        start = True
        for document in tree.xpath("/author/documents/document"):
            # Transformed
            transformed, transformed_size = self.text_transform(document.text)

            # Tensor type
            tensor_type = transformed.__class__

            # Empty tensor
            if transformed.dim() == 2:
                empty = tensor_type(self.min_length, transformed.size(1))
            else:
                empty = tensor_type(self.min_length)
            # end if

            # Fill zero
            empty.fill_(0)

            # Set
            empty[:transformed.size(0)] = transformed

            # Add one empty dim
            empty = empty.unsqueeze(0)

            # Add
            if start:
                tweets = empty
                start = False
            else:
                tweets = torch.cat((tweets, empty), dim=0)
            # end if
        # end for

        # Get each images
        start = True
        for i in range(10):
            # Image path
            image_path_jpeg = os.path.join(self.root, current_idxs + "." + str(i) + ".jpeg")
            image_path_png = os.path.join(self.root, current_idxs + "." + str(i) + ".png")

            # Check existence
            if os.path.exists(image_path_jpeg):
                image_path = image_path_jpeg
            else:
                image_path = image_path_png
            # end if

            # PIL image
            try:
                im = Image.open(image_path)
            except IOError:
                im = Image.new('RGB', (10, 10))
            # end try

            # New size
            if im.width > im.height:
                height = self.image_size
                width = int(self.image_size * (im.width / im.height))
            else:
                width = self.image_size
                height = int(self.image_size * (im.height / im.width))
            # end if

            # Resize
            im.thumbnail((width, height))

            # Transformed
            transformed_image = self.image_transform(im)

            # Add empty dim
            transformed_image = transformed_image.unsqueeze(0)

            # Add image
            if start:
                images = transformed_image
                start = False
            else:
                print(images.size())
                print(transformed_image.size())
                if transformed_image.size(1) == 4:
                    print(transformed_image[0, 0])
                    print(transformed_image[0, -1])
                    plt_image = transformed_image[0]
                    plt_image = plt_image.transpose(0, 2)
                    plt.imshow(plt_image.numpy())
                    plt.show()
                # end if
                images = torch.cat((images, transformed_image), dim=0)
            # end if
        # end for

        return tweets, images, self.labels[current_idxs]
        # return tweets, self.labels[current_idxs]
    # end __getitem__

    ##############################################
    # PRIVATE
    ##############################################

    # Create the root directory
    def _create_root(self):
        """
        Create the root directory
        :return:
        """
        os.mkdir(self.root)
    # end _create_root

    # Download the dataset
    def _download(self):
        """
        Download the dataset
        :return:
        """
        # Path to zip file
        path_to_zip = os.path.join(self.root, "pan18-author-profiling.zip")

        # Download
        if not os.path.exists(path_to_zip):
            urllib.urlretrieve("http://www.nilsschaetti.com/datasets/pan18-author-profiling.zip", path_to_zip)
        # end if

        # Unzip
        zip_ref = zipfile.ZipFile(path_to_zip, 'r')
        zip_ref.extractall(self.root)
        zip_ref.close()

        # Delete zip
        os.remove(path_to_zip)
    # end _download

    # Load labels
    def _load_labels(self):
        """
        Load labels
        :return:
        """
        # Read file
        label_file = codecs.open(os.path.join(self.root, self.lang + ".txt")).read()

        # IDX to labels
        idx_to_labels = {}

        # For each line
        for line in label_file.split("\n"):
            if len(line) > 0:
                # ID and label
                idx, label = line.split(":::")

                # Save
                idx_to_labels[idx] = self.classes[label]
            # end if
        # end for

        return idx_to_labels
    # end _load_labels

    # Load dataset
    def _load(self):
        """
        Load the dataset
        :return:
        """
        # For each file
        for file_name in os.listdir(self.root):
            if u".xml" in file_name:
                # Path to the file
                path_to_file = os.path.join(self.root, file_name)

                # Load  XML
                tree = etree.parse(path_to_file)

                # Author
                author = tree.xpath("/author")[0]

                # IDXS
                idxs = file_name[:-4]

                # Check lang
                if author.get("lang") == self.lang:
                    self.idxs.append(idxs)
                # end if
            # end if
        # end for
    # end _load

# end AuthorProfilingDataset
