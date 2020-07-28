# pycae
High level wrapper for PythonOCC 0.18

## Usage example

    import pycae as occ

    box = occ.make_box(10, 10, 10)

    # explore() can return underlying topology of
    # a certain type. An `avoid` keyword argument
    # is also available.
    for f in box.explore(occ.face):

        # if no argument is provided, directly
        # underlying topology is returned
        for w in f.explore():

            print("loop\n----")

            # wires are always explored in order
            for v in w.explore(occ.vertex):

                if v.orientation() == occ.forward:
                    # geometry can be accessed as
                    # a member function
                    pt = v.point()
                    print(pt.X(), pt.Y(), pt.Z())
