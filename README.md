# nyaggle
Code for Kaggle and Offline Competitions

## Feature Engineering

### Target Encoding
```python
import pandas as pd
import numpy as np

from sklearn.model_selection import GroupKFold
from nyaggle.feature.category_encoder import TargetEncoder


train = pd.read_csv('train.csv')
test = pd.read_csv('test.csv')
all = pd.concat([train, test]).copy()

cat_cols = [c for c in train.columns if train[c].dtype == np.object]
target_col = 'y'
group_col = 'user_id'

gkf = GroupKFold(5)

# you can pass splitting information (optional)
te = TargetEncoder(split=gkf.split(train, groups=train[group_col]))

# use fit/fit_transform to train data, then apply transform to test data
train.loc[:, cat_cols] = te.fit_transform(train[cat_cols], train[target_col])
test.loc[:, cat_cols] = te.transform(test[cat_cols])

# ... or just call fit_transform to concatenated data
all.loc[:, cat_cols] = te.fit_transform(all[cat_cols], all[cat_cols])

```

### NLP

```python
import pandas as pd
import numpy as np

from nyaggle.feature.nlp import BertSentenceVectorizer


train = pd.read_csv('train.csv')
test = pd.read_csv('test.csv')
all = pd.concat([train, test]).copy()

text_cols = ['body']
target_col = 'y'
group_col = 'user_id'


bv = BertSentenceVectorizer()

text_vector = bv.fit_transform(train[text_cols])

```
