# pywhist

A package containing the logic for the card game Whist and its variants.


## How to install

```
pip install whist
```

## How to use

`whist` contains a wide range of utility to work with playing cards and perform Whist game logic.


### Playing with cards

```python
>>> from whist.cards import Deck
>>> deck = Deck.full_deck()
>>> deck.shuffle()
>>> cards = [card.symbol for card in deck.cards]
>>> print(cards[:3])
['🃙', '🂥', '🂦']
```


### Interactive play

```
$ python -m whist.game

=== Turn: north ===

  east: 🂠 🂠 🂠 🂠 🂠 🂠 🂠 🂠 🂠 🂠 🂠 🂠 🂠
 south: 🂠 🂠 🂠 🂠 🂠 🂠 🂠 🂠 🂠 🂠 🂠 🂠 🂠
  west: 🂠 🂠 🂠 🂠 🂠 🂠 🂠 🂠 🂠 🂠 🂠 🂠 🂠

Your partner: south

Pile:

Your hand: 🃖 🃛 🃂 🃆 🃇 🃋 🂴 🂹 🂺 🂽 🂢 🂩 🂫

Actions:
 0: 🃖
 1: 🃛
 2: 🃂
 3: 🃆
 4: 🃇
 5: 🃋
 6: 🂴
 7: 🂹
 8: 🂺
 9: 🂽
10: 🂢
11: 🂩
12: 🂫
>
```