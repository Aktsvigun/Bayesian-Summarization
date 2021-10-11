import os
import tempfile
import unittest
import mock

from transformers import AutoTokenizer, PegasusForConditionalGeneration, PegasusConfig

from src.loaders import init_loader
from test.test_loaders import write_test_json, create_test_loader
from test.testing_common_utils import ids_tensor, floats_tensor, values_tensor
from src.bayesian import BayesianSummarizer


class TestBayesianSummarizer(unittest.TestCase):
    @mock.patch("src.bayesian.convert_bayesian_model")
    def setUp(self, mock_mc_model) -> None:
        self.batch_size = 2
        self.num_beams = 3
        self.sequence_length = 10
        self.vocab_size = 99

        dummy_config = PegasusConfig()
        self.model = PegasusForConditionalGeneration(config=dummy_config)
        self.tokenizer = AutoTokenizer.from_pretrained("google/pegasus-xsum")

        mock_mc_model.return_value = self.model
        self.bayesian_summarizer = BayesianSummarizer(model=self.model, tokenizer=self.tokenizer)

    def tearDown(self) -> None:
        del self.bayesian_summarizer, self.tokenizer, self.model

    @mock.patch("transformers.PegasusForConditionalGeneration.generate")
    def test_mc_dropout(self, mock_generation):
        input_text = "This is the first sentence. This is the second sentence. This is the third sentence."
        target_text = "This is a generated summary."
        mock_input_ids = [[182, 117, 109, 211, 5577, 107, 182, 117, 109, 1]]
        mock_input_ids_tensor = values_tensor(mock_input_ids)
        mock_gen_ids = [[182, 117, 114, 3943, 5627,  107, 1]]
        mock_gen_ids_tensor = values_tensor(mock_gen_ids)
        batch = {
            "document": input_text,
        }

        mock_generation.return_value = {
            "sequences": mock_gen_ids_tensor,
        }
        generations, input_ids = self.bayesian_summarizer.run_mc_dropout(
            batch,
            "cpu",
            "document",
            self.sequence_length,
            self.num_beams,
            3)

        self.assertEqual(generations[0][0], target_text)
        self.assertListEqual(input_ids[0].tolist(), mock_input_ids_tensor[0].tolist())

    @mock.patch("transformers.PegasusForConditionalGeneration.generate")
    def test_generate_bayesian(self, mock_generation):
        mock_gen_ids = [[182, 117, 114, 3943, 5627, 107, 1]]
        mock_gen_ids_tensor = values_tensor(mock_gen_ids)
        args = {
            "test_batch_size": 1,
            "dataset_name": None,
            "dataset_config_name": "",
            "max_test_samples": 4,
        }
        with tempfile.TemporaryDirectory() as tmp_dir:
            test_loader = create_test_loader(args=args, tmp_dir=tmp_dir)

            mock_generation.return_value = {
                "sequences": mock_gen_ids_tensor,
            }
            generated_sums, target_sums, article_ids, bleuvars = self.bayesian_summarizer.generate_bayesian_summaries(
                dataloader=test_loader,
                device="cpu",
                text_column="document",
                summary_column="summary",
                max_source_length=self.sequence_length,
                num_beams=self.num_beams,
                n=3)

            self.assertEqual(len(generated_sums), args["max_test_samples"])
            self.assertEqual(len(target_sums), args["max_test_samples"])
            self.assertEqual(len(article_ids), args["max_test_samples"])
            self.assertEqual(len(bleuvars), args["max_test_samples"])

            del test_loader

    @mock.patch("transformers.PegasusForConditionalGeneration.generate")
    def test_generate_mc_summaries(self, mock_generation):
        mock_gen_ids = [[182, 117, 114, 3943, 5627, 107, 1]]
        mock_gen_ids_tensor = values_tensor(mock_gen_ids)
        args = {
            "test_batch_size": 1,
            "dataset_name": None,
            "dataset_config_name": "",
            "max_test_samples": 4,
        }
        with tempfile.TemporaryDirectory() as tmp_dir:
            test_loader = create_test_loader(args=args, tmp_dir=tmp_dir)

            mock_generation.return_value = {
                "sequences": mock_gen_ids_tensor,
            }
            generated_sums = self.bayesian_summarizer.generate_mc_summaries(
                test_loader,
                device="cpu",
                text_column="document",
                max_source_length=self.sequence_length,
                num_beams=self.num_beams,
                n=3)

            self.assertEqual(len(generated_sums), args["max_test_samples"])
            self.assertEqual(len(generated_sums[0]), 3)

            del test_loader
