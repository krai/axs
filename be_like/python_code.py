#!/usr/bin/env python3

""" Example entry that is not a part of any collection.

    It contains one function: meme()
"""


def meme(does, quality, person='Bill', be='Be'):
    """ Construct the stick-figure Bill meme from supplied parameters

        Usage examples:
            clic be_like meme "finds and fixes an error in Wikipedia" smart
            clic dont_be_like meme 'wrote an OS that everybody hates' selfish
    """

    return f"\nThis is {person}.\n\n{person} {does}.\n\n{person} is {quality}.\n\n{be} like {person}.\n"


if __name__ == '__main__':

    # When the entry's code is run as a script, perform local tests:
    #
    print(f"meme('does not instagram her food', 'considerate', 'Mary') = {meme('does not instagram her food', 'considerate', 'Mary')}")
