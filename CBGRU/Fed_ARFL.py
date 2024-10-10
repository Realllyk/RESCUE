import copy
import gc
import torch
import torch.nn as nn
import torch.nn.functional as F
from options import parse_args
from data_processing.dataloader_manager import gen_arfl_dl, gen_cbgru_valid_dl
from models.ClassiFilerNet import ClassiFilerNet
from trainers.server import ARFL_Server
from trainers.client import Fed_ARFL_client
from global_test import global_test


if __name__ == '__main__':
    args = parse_args()
    criterion = nn.CrossEntropyLoss()
    if args.device != "cpu":
        device = torch.device(args.device if torch.cuda.is_available() else "cpu")
    else:
        device = torch.device("cpu")

    clients = list()
    input_size, time_stamp = 0, 0
    for i in range(args.client_num):
        noise_dl, num_train_samples, input_size, time_stamp = gen_arfl_dl(i, args.vul, args.noise_type, args.noise_rate, args.batch)
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

    global_model = ClassiFilerNet(input_size, time_stamp)
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
    
    test_dl = gen_cbgru_valid_dl(args.vul, 0, args.batch)
    global_test(server.global_model, test_dl, criterion, args, 'Fed_ARFL')



        

        

        