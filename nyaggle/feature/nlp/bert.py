from typing import List, Optional
import torch
import transformers

import numpy as np
import pandas as pd
from sklearn.decomposition import TruncatedSVD
from tqdm import tqdm

from nyaggle import Language, PoolingStrategy
from nyaggle.feature.base import BaseFeaturizer


class BertSentenceVectorizer(BaseFeaturizer):
    """Sentence Vectorizer using BERT pretrained model.

    Extract fixed-length feature vector from English/Japanese variable-length sentence using BERT.

    Args:
        lang:
            Language (EN/JP)
        n_components:
            Number of components in SVD. If `None`, SVD is not applied.
        text_columns:
            List of processing columns. If `None`, all object columns are regarded as text column.
        pooling_strategy:
            Algorithm to convert sentence-level vector to fixed-length vector.
        use_cuda:
            If `True`, inference is performed on GPU.
        tokenizer:
            The custom tokenizer used instead of default tokenizer
        model:
            The custom pretrained model used instead of default BERT model
    """

    def __init__(self, lang: Language = Language.EN, n_components: Optional[int] = None,
                 text_columns: List[str] = None, pooling_strategy: PoolingStrategy = PoolingStrategy.REDUCE_MEAN,
                 use_cuda: bool = False, tokenizer: transformers.PreTrainedTokenizer = None,
                 model: transformers.PreTrainedModel = None):
        if tokenizer is not None:
            assert model is not None
            self.tokenizer = tokenizer
            self.model = model
        if lang == Language.EN:
            self.tokenizer = transformers.BertTokenizer.from_pretrained('bert-base-uncased')
            self.model = transformers.BertModel.from_pretrained('bert-base-uncased')
        elif lang == Language.JP:
            self.tokenizer = transformers.BertJapaneseTokenizer.from_pretrained('bert-base-japanese-whole-word-masking')
            self.model = transformers.BertModel.from_pretrained('bert-base-japanese-whole-word-masking')
        else:
            raise ValueError(f'Specified language type ({lang}) is invalid.')

        self.lang = lang
        self.n_components = n_components
        self.text_columns = text_columns
        self.pooling_strategy = pooling_strategy
        self.use_cuda = use_cuda
        self.lsa = {}

    def _process_text(self, text: str) -> np.ndarray:
        tokens_tensor = torch.tensor([self.tokenizer.encode(text, add_special_tokens=True)])
        if self.use_cuda:
            tokens_tensor = tokens_tensor.to('cuda')
            self.model.to('cuda')

        self.model.eval()
        with torch.no_grad():
            all_encoder_layers, _ = self.model(tokens_tensor)

        embedding = all_encoder_layers.cpu().numpy()[0]
        if self.pooling_strategy == PoolingStrategy.REDUCE_MEAN:
            return np.mean(embedding, axis=0)
        elif self.pooling_strategy == PoolingStrategy.REDUCE_MAX:
            return np.max(embedding, axis=0)
        elif self.pooling_strategy == PoolingStrategy.REDUCE_MEAN_MAX:
            return np.r_[np.max(embedding, axis=0), np.mean(embedding, axis=0)]
        elif self.pooling_strategy == PoolingStrategy.CLS_TOKEN:
            return embedding[0]
        else:
            raise ValueError("specify valid pooling_strategy: {REDUCE_MEAN, REDUCE_MAX, REDUCE_MEAN_MAX, CLS_TOKEN}")

    def fit(self, X: pd.DataFrame, y=None):
        tqdm.pandas()
        columns = self.text_columns or [c for c in X.columns if X[c].dtype == np.object]

        for c in columns:
            emb = X[c].progress_apply(lambda x: self._process_text(x))

            if self.n_components and self.n_components < emb.shape[1]:
                self.lsa[c] = TruncatedSVD(n_components=self.n_components, algorithm='arpack')
                self.lsa[c].fit(emb)

        return self

    def transform(self, X: pd.DataFrame, y=None):
        tqdm.pandas()
        columns = self.text_columns or [c for c in X.columns if X[c].dtype == np.object]

        processed = []
        for c in columns:
            emb = X[c].progress_apply(lambda x: self._process_text(x))

            if self.n_components and self.n_components < emb.shape[1]:
                processed.append(self.lsa[c].transform(emb))
            else:
                processed.append(emb)

        return np.hstack(processed)

    def fit_transform(self, X: pd.DataFrame, y=None, **fit_params):
        tqdm.pandas()
        columns = self.text_columns or [c for c in X.columns if X[c].dtype == np.object]

        processed = []
        for c in columns:
            emb = np.vstack(X[c].progress_apply(lambda x: self._process_text(x)))

            if self.n_components and self.n_components < emb.shape[1]:
                self.lsa[c] = TruncatedSVD(n_components=self.n_components, algorithm='arpack', random_state=0)
                processed.append(self.lsa[c].fit_transform(emb))
            else:
                processed.append(emb)

        return np.hstack(processed)

