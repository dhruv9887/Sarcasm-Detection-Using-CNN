# -*- coding: utf-8 -*-
## Sarcasm Detection using Convolutional Neural Networks

#we will use GoogleNews-vectors-negative300.bin.gz dataset to train the model and then we will apply the trained model on Sarcasm_Headlines_Dataset_v2.json dataset for sarcasm detection.

### Importing the libraries

import pandas as pd
import numpy as np
import re
import json
import gensim
import math
import nltk
nltk.download('stopwords')
nltk.download('wordnet')
from nltk.corpus import stopwords
from nltk.stem.porter import PorterStemmer
from nltk.stem.snowball import SnowballStemmer
from nltk.stem.wordnet import WordNetLemmatizer
from gensim.models import KeyedVectors
import keras
from keras.models import Sequential, Model
from keras import layers
from keras.layers import Dense, Dropout, Conv1D, GlobalMaxPooling1D
import h5py

"""### Reading data"""

def parse_data(file):
    for l in open(file,'r'):
        yield json.loads(l)

from google.colab import drive
drive.mount('/content/drive')

data = list(parse_data('/content/drive/MyDrive/Sarcasm_Headlines_Dataset_v2.json'))
df = pd.DataFrame(data)

"""### Basic Data Understanding"""

df.head(5)

"""### Sarcastic Headline"""

df['headline'][4]

"""### Non-sarcastic Headline"""

df['headline'][1]

df.pop('article_link')

df.head(5)

len(df)

classes = np.unique(np.array(df['is_sarcastic']))
classes

"""### Data preprocessing"""

def text_clean(corpus):
    '''
    Purpose : Function to keep only alphabets, digits and certain words (punctuations, qmarks, tabs etc. removed)

    Input : Takes a text corpus, 'corpus' to be cleaned along with a list of words, 'keep_list', which have to be retained
            even after the cleaning process

    Output : Returns the cleaned text corpus

    '''
    cleaned_corpus = pd.Series()
    for row in corpus:
        qs = []
        for word in row.split():
            p1 = re.sub(pattern='[^a-zA-Z0-9]',repl=' ',string=word)
            p1 = p1.lower()
            qs.append(p1)
        cleaned_corpus = cleaned_corpus.append(pd.Series(' '.join(qs)))
    return cleaned_corpus

def stopwords_removal(corpus):
    stop = set(stopwords.words('english'))
    corpus = [[x for x in x.split() if x not in stop] for x in corpus]
    return corpus

def lemmatize(corpus):
    lem = WordNetLemmatizer()
    corpus = [[lem.lemmatize(x, pos = 'v') for x in x] for x in corpus]
    return corpus

def stem(corpus, stem_type = None):
    if stem_type == 'snowball':
        stemmer = SnowballStemmer(language = 'english')
        corpus = [[stemmer.stem(x) for x in x] for x in corpus]
    else :
        stemmer = PorterStemmer()
        corpus = [[stemmer.stem(x) for x in x] for x in corpus]
    return corpus

def preprocess(corpus, cleaning = True, stemming = False, stem_type = None, lemmatization = False, remove_stopwords = True):

    '''
    Purpose : Function to perform all pre-processing tasks (cleaning, stemming, lemmatization, stopwords removal etc.)

    Input :
    'corpus' - Text corpus on which pre-processing tasks will be performed

    'cleaning', 'stemming', 'lemmatization', 'remove_stopwords' - Boolean variables indicating whether a particular task should
                                                                  be performed or not
    'stem_type' - Choose between Porter stemmer or Snowball(Porter2) stemmer. Default is "None", which corresponds to Porter
                  Stemmer. 'snowball' corresponds to Snowball Stemmer

    Note : Either stemming or lemmatization should be used. There's no benefit of using both of them together

    Output : Returns the processed text corpus

    '''
    if cleaning == True:
        corpus = text_clean(corpus)

    if remove_stopwords == True:
        corpus = stopwords_removal(corpus)
    else :
        corpus = [[x for x in x.split()] for x in corpus]

    if lemmatization == True:
        corpus = lemmatize(corpus)


    if stemming == True:
        corpus = stem(corpus, stem_type)

    corpus = [' '.join(x) for x in corpus]


    return corpus

df['headline']

headlines = preprocess(df['headline'], lemmatization = True, remove_stopwords = True)

headlines[0:5]

"""### Loading Word2Vec Model"""

#model = KeyedVectors.load_word2vec_format('GoogleNews-vectors-negative300.bin', binary=True)

EMBEDDING_FILE = 'https://drive.google.com/file/d/1-6VbRsUMvb4TuYxUGQxZ8rbxPaEStPxu/view?usp=drivesdk'
model = KeyedVectors.load_word2vec_format(EMBEDDING_FILE, binary=True)

"""### Defining model parameters"""

MAX_LENGTH = 10
VECTOR_SIZE = 300

"""### Data Vectorization and Standardization"""

def vectorize_data(data):
    vectors = []

    padding_vector = [0.0] * VECTOR_SIZE

    for i, data_point in enumerate(data):
        data_point_vectors = []
        count = 0

        tokens = data_point.split()
        for token in tokens:
            if count >= MAX_LENGTH:
                break
            if token in model.key_to_index:#wv.vocab:
                data_point_vectors.append(model[token])#wv[token])
            count = count + 1

        if len(data_point_vectors) < MAX_LENGTH:
            to_fill = MAX_LENGTH - len(data_point_vectors)
            for _ in range(to_fill):
                data_point_vectors.append(padding_vector)

        vectors.append(data_point_vectors)

    return vectors

vectorized_headlines = vectorize_data(headlines)

"""### Data Validation"""

for i, vec in enumerate(vectorized_headlines):
    if len(vec) != MAX_LENGTH:
        print(i)

len(vectorized_headlines[1])

len(vectorized_headlines)

"""### Train Test Split and Conversion of Data Into Form expected by Convolutional Neural Network"""

train_div = math.floor(0.7 * len(vectorized_headlines))
train_div

X_train = vectorized_headlines[:train_div]
y_train = df['is_sarcastic'][:train_div]
X_test = vectorized_headlines[train_div:]
y_test = df['is_sarcastic'][train_div:]

print('The size of X_train is:', len(X_train), '\nThe size of y_train is:', len(y_train),
      '\nThe size of X_test is:', len(X_test), '\nThe size of y_test is:', len(y_test))

X_train = np.reshape(X_train, (len(X_train), MAX_LENGTH, VECTOR_SIZE))
X_test = np.reshape(X_test, (len(X_test), MAX_LENGTH, VECTOR_SIZE))
y_train = np.array(y_train)
y_test = np.array(y_test)

"""### Defining Neural Network Model Parameters"""

FILTERS=8
KERNEL_SIZE=3
HIDDEN_LAYER_1_NODES=10
HIDDEN_LAYER_2_NODES=5
DROPOUT_PROB=0.35
NUM_EPOCHS=10
BATCH_SIZE=50

"""### Defining our CNN+FeedForward Neural Network for Detecting Sarcasm"""

model = Sequential()

model.add(Conv1D(FILTERS,
                 KERNEL_SIZE,
                 padding='same',
                 strides=1,
                 activation='relu',
                 input_shape = (MAX_LENGTH, VECTOR_SIZE)))
model.add(GlobalMaxPooling1D())
model.add(Dense(HIDDEN_LAYER_1_NODES, activation='relu'))
model.add(Dropout(DROPOUT_PROB))
model.add(Dense(HIDDEN_LAYER_2_NODES, activation='relu'))
model.add(Dropout(DROPOUT_PROB))
model.add(Dense(1, activation='sigmoid'))
print(model.summary())

"""### Model building and training"""

model.compile(loss='binary_crossentropy', optimizer='adam', metrics=['accuracy'])

training_history = model.fit(X_train, y_train, epochs=NUM_EPOCHS, batch_size=BATCH_SIZE)

"""### Model Evaluation"""

loss, accuracy = model.evaluate(X_test, y_test, verbose=False)
print("Testing Accuracy:  {:.4f}".format(accuracy))

"""saving model

"""

model_structure = model.to_json()
with open("/content/drive/MyDrive/sarcasm_detection_model_cnn.json", "w") as json_file:
    json_file.write(model_structure)
model.save_weights("/content/drive/MyDrive/sarcasm_detection_model_cnn.h5")
