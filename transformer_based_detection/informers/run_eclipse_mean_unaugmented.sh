#!/usr/bin/env bash

# Predetermined randomized seeds to ensure replicability
declare -a seeds=(7 129 28 192 85 148 142 30 78 33)

for seed in ${seeds[@]}
do
    # MSE model
    python3 informers.py --seed=${seed} --data="ECLIPSE_MEAN" --features="M" --freq="s" --checkpoints="./checkpoints" --seq_len=16 --label_len=8 --pred_len=1 --enc_in=640 --dec_in=640 --c_out=640 --d_model=512 --n_heads=8 --e_layers=1 --d_layers=4 --d_ff=2048 --factor=1 --padding=0 --dropout=0.05 --loss="MSE" --learning_rate=0.001 --num_workers=0 --train_epochs=4 --batch_size=128 --apply_augmentations --augmentations 'Roll:0,1' 'Roll:0,1' 'Roll:0,1' 'Roll:0,1' 'Roll:0,1' 'Roll:0,1' 'Roll:0,1' 'Roll:0,1'

    # SMSE model
    python3 informers.py --seed=${seed} --data="ECLIPSE_MEAN" --features="M" --freq="s" --checkpoints="./checkpoints" --seq_len=64 --label_len=32 --pred_len=1 --enc_in=640 --dec_in=640 --c_out=640 --d_model=512 --n_heads=8 --e_layers=3 --d_layers=2 --d_ff=2048 --factor=5 --padding=0 --dropout=0.05 --loss="SMSE" --num_workers=0 --train_epochs=4 --batch_size=64 --apply_augmentations --augmentations 'Roll:0,1' 'Roll:0,1' 'Roll:0,1' 'Roll:0,1' 'Roll:0,1' 'Roll:0,1' 'Roll:0,1' 'Roll:0,1'
done
