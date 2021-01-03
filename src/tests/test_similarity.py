from tests import PySparkTestCase

import pyspark.sql.functions as f
from pyspark.sql.types import *

from similarity import Similarity

import pandas as pd


class TestSimiarity(PySparkTestCase):

    def test_check_is_spark_data_frame(self):

        df_simple_table = self.spark.read.csv('tests/fixtures/similarity/simple_table.csv', header=True)
        pd_df_simple_table = pd.read_csv('tests/fixtures/similarity/simple_table.csv')

        Similarity(df_features=df_simple_table)

        with self.assertRaises(AssertionError):
            Similarity(df_features=pd_df_simple_table)

    def test_check_nulls_in_feature_columns(self):

        df_nulls_features = self.spark.read.csv('tests/fixtures/similarity/nulls_features.csv', header=True)
        df_no_nulls_features = self.spark.read.csv('tests/fixtures/similarity/no_nulls_features.csv', header=True)

        Similarity(df_features=df_no_nulls_features)

        with self.assertRaises(AssertionError):
            Similarity(df_features=df_nulls_features)

    def test_check_is_numerical_data(self):

        df_numerical = self.spark.read.csv('tests/fixtures/similarity/numerical_data.csv', header=True)

        columns_to_convert = [col for col in df_numerical.columns if 'id' not in col]
        df_numerical_int = df_numerical
        df_numerical_float = df_numerical

        for col in columns_to_convert:
            df_numerical_int = df_numerical_int.withColumn(col, f.col(col).cast(IntegerType()))
            df_numerical_float = df_numerical_float.withColumn(col, f.col(col).cast(DoubleType()))

        Similarity(df_features=df_numerical_int)
        Similarity(df_features=df_numerical_float)

        with self.assertRaises(AssertionError):
            Similarity(df_features=df_numerical)

    def test_generate(self):

        df_features = self.spark.read.csv('tests/fixtures/similarity/features.csv', header=True)

        columns_to_convert = [col for col in df_features.columns if 'id' not in col]
        df_features_int = df_features
        for col in columns_to_convert:
            df_features_int = df_features_int.withColumn(col, f.col(col).cast(IntegerType()))

        similarity_cos = Similarity(df_features=df_features_int, similarity_type='cosine')

        pd_df_similarity_cos, mat_similarity_cos, _ = similarity_cos.generate()

        self.assertEqual(pd_df_similarity_cos.shape[0], df_features.count())
        self.assertEqual(pd_df_similarity_cos.shape[1], df_features.count())

        self.assertEqual(mat_similarity_cos.shape[0], df_features.count())
        self.assertEqual(mat_similarity_cos.shape[1], df_features.count())

        similarity_euc = Similarity(df_features=df_features_int, similarity_type='euclidean')

        pd_df_similarity_euc, mat_similarity_euc, _ = similarity_euc.generate()

        self.assertEqual(pd_df_similarity_euc.shape[0], df_features.count())
        self.assertEqual(pd_df_similarity_euc.shape[1], df_features.count())

        self.assertEqual(mat_similarity_euc.shape[0], df_features.count())
        self.assertEqual(mat_similarity_euc.shape[1], df_features.count())

        similarity_fail = Similarity(df_features=df_features_int, similarity_type='test')
        with self.assertRaises(ValueError):
            similarity_fail.generate()

    def test_convert_to_long_format(self):

        pd_df_similarities_wide = pd.read_csv('tests/fixtures/similarity/similarities_wide.csv', index_col=0)

        pd_df_similarities_long = Similarity.convert_to_long_format(pd_df_similarities_wide)

        self.assertEqual(pd_df_similarities_long.shape[0],
                         pd_df_similarities_wide.shape[0]*pd_df_similarities_wide.shape[1])

        check_1_3 = pd_df_similarities_long.loc[(pd_df_similarities_long['recipe_id_1'] == 1)
                                                & (pd_df_similarities_long['recipe_id_2'] == '3')]['similarity'].values[0]
        self.assertEqual(check_1_3, 9)

        check_3_1 = pd_df_similarities_long.loc[(pd_df_similarities_long['recipe_id_1'] == 3)
                                                & (pd_df_similarities_long['recipe_id_2'] == '1')]['similarity'].values[0]
        self.assertEqual(check_3_1, 6)

        check_2_3 = pd_df_similarities_long.loc[(pd_df_similarities_long['recipe_id_1'] == 2)
                                                & (pd_df_similarities_long['recipe_id_2'] == '3')]['similarity'].values[0]
        self.assertEqual(check_2_3, 1)

        check_1_2 = pd_df_similarities_long.loc[(pd_df_similarities_long['recipe_id_1'] == 1)
                                                & (pd_df_similarities_long['recipe_id_2'] == '2')]['similarity'].values[0]
        self.assertEqual(check_1_2, 6)

