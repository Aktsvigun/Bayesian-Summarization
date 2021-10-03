python -u bayesian_summarization.py \
    --model_path google/pegasus-xsum --dataset_name xsum \
    --output_path varpegasus10_test \
    --text_column document \
    --summary_column summary \
    --max_source_length 256 \
    --seed 100 \
    --test_batch_size 6 \
    --num_beams 5 \
    --max_test_samples 10 \
    --mc_samples 10