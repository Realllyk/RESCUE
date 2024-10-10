import copy
import gc
import random
import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from options import parse_args
from data_processing.dataloader_manager import gen_knn_dl, gen_test_dataloader
from models.CGE_Variants import CGEVariant
from trainers.server import Server
from trainers.CGE_client import CGE_client
from options import parse_args
from CGE_test import CGE_test


if __name__ == "__main__":
    args = parse_args()

    dataloader_dict = dict()
    dataloader_dict['train'] = list()
    input_size, time_steps = 0, 0

    if args.noise_type == "diff_noise":
        noise_types = random.sample(['fn_noise', 'fn_noise', 'fn_noise', 'fn_noise', 'non_noise', 'non_noise', 'non_noise', 'non_noise'], 8)
        noise_rates = [args.noise_rate]*8
    else:
        noise_types = [args.noise_type]*8
        noise_rates = random.sample([0.2, 0.2, 0.2, 0.2, 0.3, 0.3, 0.3, 0.3], 8)
        
    for i in range(args.client_num):
        train_dl = gen_knn_dl(i, args.vul, noise_types[i], noise_rates[i], args.batch)
        dataloader_dict['train'].append(train_dl)

    criterion = nn.CrossEntropyLoss()

    global_model = CGEVariant()
    global_model = global_model.to(args.device)

    server = Server(
        args,
        global_model,
        args.device,
        criterion
    )

    test_dl = gen_test_dataloader(args.vul)
    for epoch in range(args.epoch):
        server.initialize_epoch_updates(epoch)

        for client_id in range(args.client_num):
            client = CGE_client(args,
                                criterion,
                                None,
                                args.device,
                                None,
                                dataloader_dict['train'][client_id],
                                client_id)
            client.model = copy.deepcopy(server.global_model)
            client.RCE_train()
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
        
    if args.noise_type != 'diff_noise':
        args.noise_rate = 2.3
    CGE_test(server.global_model, test_dl, criterion, args.device, args, 'non_Fed_KNN_3')