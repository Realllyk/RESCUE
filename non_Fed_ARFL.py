import copy
import gc
import random
import torch
import torch.nn as nn
import torch.nn.functional as F
from options import parse_args
from data_processing.dataloader_manager import gen_arfl_dl, gen_test_dataloader
from models.CGE_Variants import CGEVariant
from trainers.server import ARFL_Server
from trainers.CGE_client import Fed_ARFL_client
from CGE_test import CGE_test


if __name__ == '__main__':
    args = parse_args()
    criterion = nn.CrossEntropyLoss()
    if args.device != "cpu":
        device = torch.device(args.device if torch.cuda.is_available() else "cpu")
    else:
        device = torch.device("cpu")

    clients = list()

    if args.noise_type == "diff_noise":
        noise_types = random.sample(['fn_noise', 'fn_noise', 'fn_noise', 'fn_noise', 'non_noise', 'non_noise', 'non_noise', 'non_noise'], 8)
        noise_rates = [args.noise_rate]*8
    else:
        noise_types = [args.noise_type]*8
        noise_rates = random.sample([0.2, 0.2, 0.2, 0.2, 0.3, 0.3, 0.3, 0.3], 8)

    for i in range(args.client_num):
        noise_dl, num_train_samples = gen_arfl_dl(i, args.vul, noise_types[i], noise_rates[i])
        client = Fed_ARFL_client(
            args,
            criterion,
            None,
            noise_dl,
            1.,
            num_train_samples
        )
        clients.append(client)
    total_num_samples = sum([c.num_train_samples for c in clients])

    global_model = CGEVariant()
    global_model = global_model.to(device)
    server = ARFL_Server(
        args,
        global_model,
        criterion,
        args.seed,
        clients,
        total_num_samples
    )

    for c in clients:
        c.model = copy.deepcopy(global_model)
        c.test()

    for epoch in range(args.epoch):
        print(f"Epoch {epoch} Training:------------------")
        server.initialize_epoch_updates(epoch)
        server.sample_clients(epoch)

        for c in clients:
            if c.model != None:
                del c.model
            c.model = copy.deepcopy(server.global_model)
        
        for i, c in enumerate(server.selected_clients):
            c.train()
            print(f"Selected Client {i} Train Loss: {c.result['loss']}")

        server.average_weights()
        server.update_alpha()
    

    test_dl = gen_test_dataloader(args.vul)
    if args.noise_type != 'diff_noise':
        args.noise_rate = 2.3
    CGE_test(server.global_model, test_dl, criterion, device, args, 'non_Fed_ARFL')



        

        

        