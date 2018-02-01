package it.unibo.alchemist.loader.export

import it.unibo.alchemist.model.interfaces.Incarnation
import it.unibo.alchemist.model.interfaces.Environment
import it.unibo.alchemist.model.interfaces.Reaction
import java.util.stream.DoubleStream
import it.unibo.alchemist.model.interfaces.Molecule
import it.unibo.alchemist.model.interfaces.Time;
import it.unibo.alchemist.model.interfaces.Node
import gnu.trove.map.TIntDoubleMap
import gnu.trove.map.hash.TIntDoubleHashMap
import com.google.common.collect.MapMaker
import it.unibo.alchemist.model.interfaces.Position
import it.unibo.alchemist.model.implementations.times.DoubleTime
import it.unibo.alchemist.kotlin.*

class DistanceTraveled (
    filter: FilteringPolicy,
    aggregators: List<String>
) : AggregableExtractor(filter, aggregators, DistanceTraveled::class.simpleName) {
    private val odometer = PartialOdometer()
    override fun <T> extractOnNode(env: Environment<T>, n: Node<T>, r: Reaction<T>?, time: Time?, step: Long) =
        odometer.sample(env, n)
}

class OverallDistanceTraveled (
    filter: FilteringPolicy,
    aggregators: List<String>
) : AggregableExtractor(filter, aggregators, OverallDistanceTraveled::class.simpleName) {
    private val tracker = Tracker<Double, Double>()
    private val odometer = PartialOdometer()
    override fun <T> extractOnNode(env: Environment<T>, n: Node<T>, r: Reaction<T>?, time: Time?, step: Long) =
        tracker.sample(n, (tracker.get(n) ?: 0.0) + odometer.sample(env, n)) { cur, _ -> cur }
}

class CurrentSpeed (
    filter: FilteringPolicy,
    aggregators: List<String>
) : AggregableExtractor(filter, aggregators, CurrentSpeed::class.simpleName) {
    private val odometer = PartialOdometer()
    private val stopwatch = StopWatch()
    override fun <T> extractOnNode(env: Environment<T>, n: Node<T>, r: Reaction<T>?, time: Time, step: Long) =
        odometer.sample(env, n) / stopwatch.sample(n, time)
}

private class PartialOdometer {
    private val tracker = Tracker<Position, Double>()
    fun <T> sample(env: Environment<T>, n: Node<T>): Double = tracker.sample(n, env.getPosition(n)) {
            current, old -> current.getDistanceTo(old)
        }
}

private class StopWatch {
    private val tracker = Tracker<Time, Double>()
    fun sample(n: Node<*>, t: Time) = tracker.sample(n, t) {
            current, old -> (current - old).toDouble()
        }
}

private class Tracker<V, O> {
    private val previously: MutableMap<Node<*>, V> = MapMaker().weakKeys().makeMap()
    inline fun sample(n: Node<*>, current: V, reduce: (V, V) -> O): O =
        current.let { reduce(current, previously.put(n, current) ?: current ) }
    fun get(n: Node<*> ): V? = previously.get(n)
}

