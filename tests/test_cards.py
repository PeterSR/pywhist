from whist.cards import Suit, Rank, Card, Deck


def test_card():
    card = Card(Suit.Club, Rank.Seven)

    assert card.suit.symbol == "♣"
    assert card.rank.symbol == "7"
    assert card.symbol == "🃗"


def test_deck():
    c1 = Card(Suit.Spade, Rank.Ace)
    c2 = Card(Suit.Club, Rank.Seven)
    c3 = Card(Suit.Club, Rank.Ace)

    deck = Deck([c1, c2, c3])

    assert len(deck) == 3

    deck.sort()

    assert [card for card in deck] == [c2, c3, c1]


def test_deck_full():
    deck = Deck.full_deck()

    assert len(deck) == 55


def test_deck_give_take():
    c1 = Card(Suit.Spade, Rank.Ace)
    c2 = Card(Suit.Club, Rank.Seven)
    c3 = Card(Suit.Club, Rank.Ace)

    deck = Deck([c1, c2, c3])

    deck.take(c1)

    assert len(deck) == 2
    assert c1 not in deck

    deck.give(c1)

    assert len(deck) == 3
    assert c1 in deck


def test_pile():
    c1 = Card(Suit.Spade, Rank.Ace)
    c2 = Card(Suit.Club, Rank.Seven)
    c3 = Card(Suit.Club, Rank.Ace)

    deck = Deck.empty_pile()
    deck.give(c1)
    deck.give(c2)
    deck.give(c3)

    assert [card for card in deck] == [c1, c2, c3]

    deck.sort()

    assert [card for card in deck] == [c1, c2, c3]
