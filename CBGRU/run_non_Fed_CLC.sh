# noise_rates=(0.05 0.1 0.15 0.2 0.25 0.3)
noise_rates=(0.3)
# noise_rates=(0.5 0.6 0.7 0.8 0.9 1.0)
vuls=("reentrancy" "timestamp")
device="$1"

for vul in "${vuls[@]}"
do
    for noise_rate in "${noise_rates[@]}"
    do
    # 对每个噪声值运行五次
    for i in {1..10}
    do
        python non_Fed_CLC.py --vul $vul --noise_type diff_noise --noise_rate $noise_rate  --device "$device" --batch 8 --input_channel 428
    done
    done
done