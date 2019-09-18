#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# train backbone network with imagenet dataset
#

import argparse
import numpy as np

from tensorflow.keras.optimizers import Adam, SGD
from tensorflow.keras.preprocessing.image import ImageDataGenerator
from tensorflow.keras.applications.resnet50 import preprocess_input, decode_predictions
from tensorflow.keras.callbacks import TensorBoard, ModelCheckpoint, ReduceLROnPlateau, LearningRateScheduler, EarlyStopping, TerminateOnNaN, LambdaCallback, CSVLogger
from shufflenet import ShuffleNet
from shufflenet_v2 import ShuffleNetV2


def preprocess(x):
    x = np.expand_dims(x, axis=0)
    x = preprocess_input(x)
    x /= 255.0
    x -= 0.5
    x *= 2.0
    return x


def main(args):
    log_dir = 'logs/'
    groups = 3

    # prepare model
    model = ShuffleNet(groups=groups, pooling='avg')
    if args.weights_path:
        model.load_weights(args.weights_path, by_name=True)

    # callbacks for training process
    checkpoint = ModelCheckpoint(log_dir + 'ep{epoch:03d}-val_loss{val_loss:.3f}-val_acc{val_acc:.3f}.h5',
        monitor='val_acc',
        mode='max',
        verbose=1,
        save_weights_only=False,
        save_best_only=True,
        period=1)
    logging = TensorBoard(log_dir=log_dir, histogram_freq=0, write_graph=False, write_grads=False, write_images=False, update_freq='batch')
    terminate_on_nan = TerminateOnNaN()
    learn_rates = [0.05, 0.01, 0.005, 0.001, 0.0005]
    lr_scheduler = LearningRateScheduler(lambda epoch: learn_rates[epoch // 30])

    # data generator
    train_datagen = ImageDataGenerator(preprocessing_function=preprocess,
                                       zoom_range=0.25,
                                       width_shift_range=0.05,
                                       height_shift_range=0.05,
                                       horizontal_flip=True)

    test_datagen = ImageDataGenerator(preprocessing_function=preprocess)

    train_generator = train_datagen.flow_from_directory(
            args.train_data_path,
            target_size=(224, 224),
            batch_size=args.batch_size)

    test_generator = test_datagen.flow_from_directory(
            args.val_data_path,
            target_size=(224, 224),
            batch_size=args.batch_size)


    # start training
    model.compile(
              optimizer=SGD(lr=.05, decay=5e-4, momentum=0.9),
              metrics=['accuracy'],
              loss='categorical_crossentropy')

    model.fit_generator(
            train_generator,
            steps_per_epoch=train_generator.samples // args.batch_size,
            epochs=args.total_epoch,
            workers=7,
            initial_epoch=args.init_epoch,
            use_multiprocessing=False,
            validation_data=test_generator,
            validation_steps=test_generator.samples // args.batch_size,
            callbacks=[logging, checkpoint, lr_scheduler, terminate_on_nan])

    # Finally store model
    model.save(log_dir + 'trained_final.h5')



if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--model_type', type=str, required=False, default='shufflenet',
        help='backbone model type: shufflenet/shufflenet_v2, default=shufflenet')
    parser.add_argument('--train_data_path', type=str, required=True,
        help='path to Imagenet train data')
    parser.add_argument('--val_data_path', type=str, required=True,
        help='path to Imagenet validation dataset')
    parser.add_argument('--weights_path', type=str,required=False, default=None,
        help = "Pretrained model/weights file for fine tune")
    parser.add_argument('--batch_size', type=int,required=False, default=128,
        help = "batch size for train, default=128")
    parser.add_argument('--init_epoch', type=int,required=False, default=0,
        help = "Initial training epochs for fine tune training, default=0")
    parser.add_argument('--total_epoch', type=int,required=False, default=300,
        help = "Total training epochs, default=300")

    args = parser.parse_args()

    main(args)
