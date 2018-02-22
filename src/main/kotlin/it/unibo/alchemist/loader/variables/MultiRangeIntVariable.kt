package it.unibo.alchemist.loader.variables

import java.lang.IllegalArgumentException

typealias RangeDescriptor = kotlin.Triple<Double, Double, Double>
class MultiRangeIntVariable(val default: Double, vararg ranges: Iterable<Double>): PrintableVariable<Double>() {
    val ranges: List<RangeDescriptor> = ranges
        .map { it.toList() }
        .map { if (it.size == 3) { RangeDescriptor(it[0], it[1], it[2]) } else { RangeDescriptor(Double.NaN, Double.NaN, Double.NaN)}}
	.toList()
    init {
        val isNaN = Double::isNaN
        if(ranges.any { it.any{ isNaN(it) } }) {
            throw IllegalArgumentException("$ranges is not a valid list of triples")
        }
    }
    override fun getDefault() = default
    override fun stream() = ranges.stream().flatMap { LinearVariable(it.first, it.first, it.second, it.third).stream() }
}