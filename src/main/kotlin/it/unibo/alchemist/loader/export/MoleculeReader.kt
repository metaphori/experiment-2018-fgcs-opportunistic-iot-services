package it.unibo.alchemist.loader.export

import it.unibo.alchemist.model.interfaces.Incarnation
import it.unibo.alchemist.model.interfaces.Environment
import it.unibo.alchemist.model.interfaces.Reaction
import java.util.stream.DoubleStream
import it.unibo.alchemist.model.interfaces.Molecule
import it.unibo.alchemist.model.interfaces.Time;
import it.unibo.alchemist.model.interfaces.Node
import java.lang.IllegalStateException

open class MoleculeReader constructor(
    protected val molecule: Molecule,
    protected val property: String?,
    filter: FilteringPolicy,
    aggregators: List<String>
) : AggregableExtractor(filter, aggregators, "${property?.let { "$it@" } ?: ""}${molecule}") {

    public constructor(
        molecule: String,
        property: String,
        incarnation: Incarnation<*>,
        filter: FilteringPolicy,
        aggregators: List<String>
    ) : this(incarnation.createMolecule(molecule), property, filter, aggregators)

    override fun <T> extractOnNode(env: Environment<T>, n: Node<T>, r: Reaction<T>?, time: Time?, step: Long) =
        env.incarnation
            .map { it.getProperty(n, molecule, property) }
            .orElseThrow {
                IllegalStateException("Failed extraction of ${property?.let { "property $it from " } ?: "" }"
                    + "molecule $molecule as the environment has no configured incarnation.")
            }
}