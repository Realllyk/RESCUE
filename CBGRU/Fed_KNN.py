import copy
import gc
import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from options import parse_args
from data_processing.dataloader_manager import gen_knn_dl, gen_cbgru_valid_dl
from models.ClassiFilerNet import ClassiFilerNet
from trainers.server import Server
from trainers.client import Fed_Avg_client
from global_test import global_test


if __name__ == "__main__":
    args = parse_args()

    dataloader_dict = dict()
    dataloader_dict['train'] = list()
    input_size, time_steps = 0, 0
    for i in range(args.client_num):
        train_dl, input_size, time_steps = gen_knn_dl(i, args.vul, args.noise_type, args.noise_rate, args.batch)
        dataloader_dict['train'].append(train_dl)

    criterion = nn.CrossEntropyLoss()

    global_model = ClassiFilerNet(input_size, time_steps)
    global_model = global_model.to(args.device)

    server = Server(
        args,
        global_model,
        args.device,
        criterion
    )

    test_dl = gen_cbgru_valid_dl(args.vul)
    for epoch in range(args.epoch):
        server.initialize_epoch_updates(epoch)

        for client_id in range(args.client_num):
            client = Fed_Avg_client(args,
                                criterion,
                                None,
                                dataloader_dict['train'][client_id])
            client.model = copy.deepcopy(server.global_model)
            client.train()
            server.save_train_updates(
                    copy.deepcopy(client.get_parameters()),
                    client.result['sample'],
                    client.result
            )
            print(f"client:{client_id}")
            client.print_loss()
            del client
            torch.cuda.empty_cache()
            gc.collect()

        server.average_weights()
        print(epoch)
    
    global_test(server.global_model, test_dl, criterion, args, 'Fed_KNN_3')

