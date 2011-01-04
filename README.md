# HotMap

**HotMap** is a proof-of-concept distributed computing framework for Python built on top of [Redis](http://redis.io) and
[HotQueue](http://richardhenry.github.com/hotqueue/).

**Author**: Jamie Matthews (<https://github.com/j4mie>)

## Installation

Clone from GitHub, for now.

## What?

Think of HotMap as a replacement for the standard library's built-in [`map` function](http://docs.python.org/library/functions.html#map).
The difference is, HotMap transparently distributes work among one or more worker processes. These processes may be running on the same
machine as your program, or a remote machine, or a thousand remote machines.

## Why is it "proof of concept?"

HotMap isn't ready for production. I wrote it in about an hour. At the moment, if one of your worker processes throws an exception or crashes,
your program will just hang forever. This can probably be fixed, but at the moment this is just a toy to try out ideas. Please fork if
you think you can help.

## But it's only 60 lines of code!

...yep. And half of those are comments.

## Concepts

A *worker* is a simple function that accepts a single argument, does some work based on it, and returns a single result. HotMap
provides a decorator to convert a function into a worker (see examples below). Workers should probably be run by some sort of
process monitoring tool like [upstart](http://upstart.ubuntu.com/) or [supervisord](http://supervisord.org/).

Once you've written a worker, you provide HotMap with an iterable (a list, say). HotMap passes each item in the list to your worker
function and gives you back another list (actually, it's a generator) that contains the results, in order. Just like `map(function, list)`.

If you have one worker process, it will deal with each item in the list in turn, one at a time. If you have multiple worker processes, they will
run in parallel. Simple.

## Imagine the possibilities...

Your program, your workers, and your Redis server could all be running on your laptop. Or you could have a cluster of a thousand machines,
each with a thousand cores, each running a thousand worker processes. Your program doesn't care, it'll just run faster.

Note: I have only tested the former case, not the latter.

## Example

Let's start by writing a worker to compute the square of its input. We'll put this in a file called `worker.py`. Because squaring a
number is a fairly fast operation, we'll put in an artificial delay to make it look like we're doing loads of really intense work.

    # worker.py

    import time
    from hotmap import HotMap

    mapper = HotMap('myqueue')

    @mapper.worker
    def square(number):
        time.sleep(1)
        return number * number

    square.wait()

Now we'll write a program that needs to compute the square of a bunch of numbers. Put this in a file called `myprogram.py`.

    # myprogram.py

    from hotmap import HotMap

    mapper = HotMap('myqueue')

    numbers_to_square = [1, 2, 3, 4, 5]
    results = mapper.map(numbers_to_square)
    print list(results) # convert to a list to exhaust the generator

OK, open up a terminal and start a worker process in the background:

    $ python worker.py &
    [1] 15469

To prove it's working, run your program and see what happens:

    $ python myprogram.py
    [1, 4, 9, 16, 25]

Notice that there was a fairly long delay before your results came back. How long did it take, exactly?

    $ time python myprogram.py
    [1, 4, 9, 16, 25]

    real    0m5.065s
    user    0m0.037s
    sys     0m0.022s

Five seconds (more or less). That's because we only have one worker process. It handles each item in your
list one at a time, and each one takes about a second (remember that `time.sleep(1)` call in the worker function?)

So, let's start a few more worker processes:

    $ for i in {1..4}; do python worker.py & done
    [2] 15810
    [3] 15811
    [4] 15812
    [5] 15813
    $ ps -ef | grep worker.py | grep -v grep | wc -l
           5

We now have five worker processes running. So, how long does our program take to run now?

    $ time python myprogram.py
    [1, 4, 9, 16, 25]

    real    0m1.060s
    user    0m0.035s
    sys     0m0.020s

About one second. That's because each of the five worker processes handles an item from your list in parallel, and
each one takes about one second.

Finally, kill your worker processes (or just close your terminal window):

    $ ps -ef | grep worker.py | grep -v grep | awk '{print $2}' | xargs kill
    [1]   Terminated              python worker.py
    [2]   Terminated              python worker.py
    [3]-  Terminated              python worker.py
    [4]+  Terminated              python worker.py

## Let's write a web scraper!

First, the worker:

    # scraperworker.py

    from urllib2 import urlopen
    from hotmap import HotMap

    mapper = HotMap('myqueue')

    @mapper.worker
    def scrape(url):
        return urlopen(url).read()

    scrape.wait()

Second, the program that controls which urls are getting scraped:

    # scrapeurls.py

    from hotmap import HotMap

    mapper = HotMap('myqueue')

    urls = [
        'http://www.j4mie.org',
        'http://www.github.com/j4mie',
        'http://www.google.com',
    ]

    results = mapper.map(urls)

    print [len(result) for result in results]

Let's try it with one worker:

    $ python scraperworker.py &
    [1] 16610

    $ python scrapeurls.py
    [28804, 51866, 9669]

    $ time python scrapeurls.py
    [28844, 51866, 9581]

    real    0m2.027s
    user    0m0.035s
    sys     0m0.020s

How about we fire up a couple more workers?

    $ python scraperworker.py &
    [2] 16682

    $ python scraperworker.py &
    [3] 16700

And try timing our program again:

    $ time python scrapeurls.py
    [28844, 51866, 9649]

    real    0m1.437s
    user    0m0.035s
    sys     0m0.020s

Not bad.

Cleanup:

    $ ps -ef | grep scraperworker.py | grep -v grep | awk '{print $2}' | xargs kill
    [1]   Terminated              python scraperworker.py
    [2]-  Terminated              python scraperworker.py
    [3]+  Terminated              python scraperworker.py

## (Un)license

This is free and unencumbered software released into the public domain.

Anyone is free to copy, modify, publish, use, compile, sell, or distribute this software, either in source code form or as a compiled binary, for any purpose, commercial or non-commercial, and by any means.

In jurisdictions that recognize copyright laws, the author or authors of this software dedicate any and all copyright interest in the software to the public domain. We make this dedication for the benefit of the public at large and to the detriment of our heirs and successors. We intend this dedication to be an overt act of relinquishment in perpetuity of all present and future rights to this software under copyright law.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

For more information, please refer to <http://unlicense.org/>
