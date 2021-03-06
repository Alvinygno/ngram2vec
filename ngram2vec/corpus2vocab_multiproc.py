# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, division
import argparse
import codecs
from sys import getsizeof
import six
from multiprocessing import Pool
from utils.vocabulary import save_count_vocabulary
from utils.misc import merge_vocabularies
import line2vocab


def corpus2vocab_process(corpus_file, proc_id, proc_num, args):
    """ 
    .
    """
    vocab = {}

    memory_size = args.memory_size * 1000**3 / proc_num
    memory_size_used = 0.0
    reduce_thr = 1
    tokens_num = 0
    
    with open(corpus_file, mode="r", encoding="utf-8") as f:
        for line_id, line in enumerate(f):
            if (line_id % proc_num) == proc_id:
                if proc_id == 0:
                    print("\r{}M tokens processed (approximately).".format(int(tokens_num*proc_num/1000**2)), end="")
                line_vocab = getattr(line2vocab, args.feature)(line, args)
                tokens_num += len(line.strip().split())
                for word, count in line_vocab.items():
                    if len(word) > args.max_length:
                        continue
                    if word not in vocab:
                        vocab[word] = count
                        memory_size_used += getsizeof(word)
                        if memory_size_used + getsizeof(vocab) > memory_size * 0.7:
                            reduce_thr += 1
                            vocab_size = len(vocab)
                            vocab = {w: c for w, c in six.iteritems(vocab) if c >= reduce_thr}
                            memory_size_used *= len(vocab) / vocab_size
                    else:
                        vocab[word] += count

    return (vocab,)


def main():
    parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("--corpus_file", type=str, required=True,
                        help="Path to the corpus file.")
    parser.add_argument("--vocab_file", type=str, required=True,
                        help="Path to the vocab file.")

    parser.add_argument("--feature", type=str, default="word",
                        choices=["word", "ngram"],
                        help="""Type of linguistic units (features) to use.
                        More types will be added. Options are
                        [word|ngram].""")
    parser.add_argument("--min_count", type=int, default=100,
                        help="Threshold for removing low-frequency features (units).")
    parser.add_argument("--max_length", type=int, default=50,
                        help="Threshold for removing features (units) with too much characters.")

    parser.add_argument("--processes_num", type=int, default=4,
                        help="Number of processes.")

    parser.add_argument("--order", type=int, default=2,
                        help="Order of word-level ngram if --feature is set to ngram")
    
    parser.add_argument("--memory_size", type=float, default=4.0,
                        help="""Memory size. Sometimes the vocabulary is large. 
                        We remove low-frequency features to ensure that vocabulary could be stored in memory.""")

    args = parser.parse_args()

    print("Corpus2vocab")

    pool = Pool(args.processes_num)
    vocab_list = []
    for i in range(args.processes_num):
        vocab_list.append((pool.apply_async(func=corpus2vocab_process, args=[args.corpus_file, i, args.processes_num, args])))
    pool.close()
    pool.join()

    vocab_list = [v.get()[0] for v in vocab_list]
    
    vocab = merge_vocabularies(vocab_list)

    # Reduce vocabulary.
    vocab = {w: c for w, c in six.iteritems(vocab) if c >= args.min_count}
    # Sort vocabulary.
    vocab = sorted(six.iteritems(vocab), key=lambda item: item[1], reverse=True)
    save_count_vocabulary(args.vocab_file, vocab)

    print ()
    print ("Size of vocabulary: {}".format(len(vocab)))
    print ("Corpus2vocab finished")


if __name__ == '__main__':
    main()

