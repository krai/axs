# C-language example (compilation and running)

The example program computes a square root of a number.
The main point is to demonstrate how compilation and 

## Direct compilation:

```
    axs byname square_root_c , run
```

## Direct execution after compilation:

```
    axs byname square_root_compiled , run --area=16
```

## Pipelined compilation and execution:

```
    axs byname square_root_c , run , run --area=25
```

## Rule-based compilation, direct execution:

```
    axs byquery compiled,square_root , run --area=36
```

## Rule-based execution:

```
    axs byquery compute,square_root,area=64
```
