# C-language example (compilation and execution)

The example program computes a square root of a number.

The main point is to demonstrate how compilation and execution are wired,
and how parameters are passed into the compiled code and the specific "experiment".

## Direct compilation:

```
    axs byname square_root_c , run
```

## Direct execution after compilation:

```
    axs byname square_root_compiled , run --area=16
```
(compile with default *area*, then set *area* to 16 for a specific run)

## Pipelined compilation and execution:

```
    axs byname square_root_c , run --area=25 , run --area=36
```
(compile with default *area*=25, then set *area* to 36 for a specific run)

## Rule-based compilation, direct execution:

```
    axs byquery compiled,square_root,area=49 , run --area=64
```
(compile with default *area*=49, then set *area* to 64 for a specific run)

