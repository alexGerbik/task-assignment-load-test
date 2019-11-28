from collections import Counter

import matplotlib.pyplot as plt


def main():
    with open('priorities.txt') as file:
        priorities = file.read().strip().split('\n')
        priorities = list(map(int, priorities))
    n = len(priorities)
    t = [(n-i, v) for i, v in enumerate(priorities)]
    diffs = [actual-expected for actual, expected in t]
    c = Counter(diffs)
    x, y = [], []
    for k, v in c.items():
        x.append(k)
        y.append(v)

    fig, ax = plt.subplots()
    ax.bar(x, y)
    plt.show()


if __name__ == '__main__':
    main()
