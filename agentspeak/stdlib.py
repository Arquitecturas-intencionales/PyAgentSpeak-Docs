# -*- coding: utf-8 -*-
#
# This file is part of the python-agentspeak interpreter.
# Copyright (C) 2016-2019 Niklas Fiekas <niklas.fiekas@tu-clausthal.de>.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.

from __future__ import print_function
from __future__ import division

import agentspeak
import agentspeak.runtime
import colorama
import random
import datetime
import collections

from agentspeak import asl_str, Literal

import agentspeak.optimizer


LOGGER = agentspeak.get_logger(__name__)


# TODO:
# * Plan Library Manipulation
#   - .add_plan
#   - .plan_label
#   - .relevant_plans
#   - .remove_plan
# * BDI
#   - .current_intention
#   - .desire
#   - .drop_all_desires
#   - .drop_all_events
#   - .drop_all_intentions
#   - .drop_desire
#   - .drop_event
#   - .drop_intention
#   - .fail_goal
#   - .intend
#   - .succeed_goal
#   - .add_anot
#   - .at
#   - .create_agent
#   - .kill_agent
#   - .perceive


actions = agentspeak.Actions()


@actions.add(".broadcast", 2)
def _broadcast(agent, term, intention):
    """
 _broadcast
 Multidifusión de mensajes entre agentes
-----
*Parámetros:
agent Agente receptor
term  Término de la ilocusión a ser transmitida: tell, untell, achieve
intention La pila de intenciones del agente emisor
 
*Regresa: Nada
-----
    """
    # Illocutionary force.
    ilf = agentspeak.grounded(term.args[0], intention.scope)
    if not agentspeak.is_atom(ilf):
        return
    if ilf.functor == "tell":
        goal_type = agentspeak.GoalType.belief
        trigger = agentspeak.Trigger.addition
    elif ilf.functor == "untell":
        goal_type = agentspeak.GoalType.belief
        trigger = agentspeak.Trigger.removal
    elif ilf.functor == "achieve":
        goal_type = agentspeak.GoalType.achievement
        trigger = agentspeak.Trigger.addition
    else:
        raise agentspeak.AslError("unknown illocutionary force: %s" % ilf)

    # Prepare message.
    message = agentspeak.freeze(term.args[1], intention.scope, {})
    tagged_message = message.with_annotation(
        agentspeak.Literal("source", (agentspeak.Literal(agent.name), )))

    # Broadcast.
    for receiver in agent.env.agents.values():
        if receiver == agent:
            continue

        receiver.call(trigger, goal_type, tagged_message, agentspeak.runtime.Intention())

    yield


@actions.add(".send", 3)
def _send(agent, term, intention):
    """
 _send
 Envía un mensaje a un agente o grupo de agentes
-----
*Parámetros:
agent El agente emisor
term  El mensaje, con fuerza ilocutoria: tell, untell, achieve
intention La pila de intenciones del agente emisor
 
*Regresa: Nada
-----
    """
    # Find the receivers: By a string, atom or list of strings or atoms.
    receivers = agentspeak.grounded(term.args[0], intention.scope)
    if not agentspeak.is_list(receivers):
        receivers = [receivers]
    receiving_agents = []
    for receiver in receivers:
        if agentspeak.is_atom(receiver):
            receiving_agents.append(agent.env.agents[receiver.functor])
        else:
            receiving_agents.append(agent.env.agents[receiver])

    # Illocutionary force.
    ilf = agentspeak.grounded(term.args[1], intention.scope)
    if not agentspeak.is_atom(ilf):
        return
    if ilf.functor == "tell":
        goal_type = agentspeak.GoalType.belief
        trigger = agentspeak.Trigger.addition
    elif ilf.functor == "untell":
        goal_type = agentspeak.GoalType.belief
        trigger = agentspeak.Trigger.removal
    elif ilf.functor == "achieve":
        goal_type = agentspeak.GoalType.achievement
        trigger = agentspeak.Trigger.addition
    else:
        raise agentspeak.AslError("unknown illocutionary force: %s" % ilf)

    # TODO: unachieve, askOne, askAll, tellHow, untellHow, askHow

    # Prepare message.
    message = agentspeak.freeze(term.args[2], intention.scope, {})
    tagged_message = message.with_annotation(
        agentspeak.Literal("source", (agentspeak.Literal(agent.name), )))

    # Broadcast.
    for receiver in receiving_agents:
        receiver.call(trigger, goal_type, tagged_message, agentspeak.runtime.Intention())

    yield


COLORS = [(colorama.Back.GREEN, colorama.Fore.WHITE),
          (colorama.Back.MAGENTA, colorama.Fore.WHITE),
          (colorama.Back.YELLOW, colorama.Fore.BLACK),
          (colorama.Back.BLUE, colorama.Fore.WHITE),
          (colorama.Back.CYAN, colorama.Fore.BLACK),
          (colorama.Back.RED, colorama.Fore.WHITE)]


@actions.add(".print")
@agentspeak.optimizer.no_scope_effects
def _print(agent, term, intention, _color_map={}, _current_color=[0]):
    """
    _print
 Imprime un término. Función auxiliar disponible para los agentes
-----
*Parámetros:
agent Agente que manda imprimir
term  Término a imprimir
intention La pila de intenciones del agente emisor
_color_map={} Mapa de colores para identificar a un agente
 _current_color=[0] Color asociado al agente
 
*Regresa: Nada
-----
    """
    if agent in _color_map:
        color = _color_map[agent]
    else:
        color = COLORS[_current_color[0]]
        _current_color[0] = (_current_color[0] + 1) % len(COLORS)
        _color_map[agent] = color

    memo = {}
    text = " ".join(asl_str(agentspeak.freeze(t, intention.scope, memo)) for t in term.args)

    with colorama.colorama_text():
        print(color[0], color[1], agent.name, colorama.Fore.RESET, colorama.Back.RESET, " ", text, sep="")

    yield


@actions.add(".fail", 0)
@agentspeak.optimizer.no_scope_effects
def _fail(agent, term, intention):
    """
 _fail
 Falla por defecto. Hace fallar una intención
-----
*Parámetros:
agent Agente dueño de la intención fallida
term  Término que identifica a la intención
intention La pila de intenciones del agente emisor
 
*Regresa: 
-----
    """
    return
    yield


@actions.add(".my_name", 1)
@agentspeak.optimizer.function_like
def _my_name(agent, term, intention):
    """
    _my_name
 Determina si el término recibido unifica con el nombre del agente consultado
-----
*Parámetros:
agent Agente consultado
term  Término a evaluar
intention Pila de intenciones
 
*Regresa: Nada
-----
    """
    if agentspeak.unify(term.args[0], Literal(agent.name), intention.scope, intention.stack):
        yield


@actions.add(".concat")
@agentspeak.optimizer.function_like
def _concat(agent, term, intention):
    """
 _concat
 Concatena dos términos que unifican en la pila de intenciones
-----
*Parámetros:
agent Agente consultado
term  Término a evaluar
intention Pila de intenciones
 
*Regresa: Nada
-----
    """
    args = [agentspeak.grounded(arg, intention.scope) for arg in term.args[:-1]]

    if all(isinstance(arg, (tuple, list)) for arg in args):
        result = tuple(el for arg in args for el in arg)
    else:
        result = "".join(str(arg) for arg in args)

    if agentspeak.unify(term.args[-1], result, intention.scope, intention.stack):
        yield


actions.add_function(".random", (), random.random)

actions.add_function(".min", (tuple, ), min)
actions.add_function(".max", (tuple, ), max)
actions.add_function(".length", (None, ), len)


@actions.add_function(".nth", (int, tuple))
def _nth(index, l):
    """
 _nth
 Devuelve el n-ésimo elemento de una lista
-----
*Parámetros:
index Índice del elemento a ser devuelto: n
l  Lista a ser consultada
 
*Regresa: El n-ésimo elemento de la lista
-----
    """
    assert index >= 0
    return l[index]


@actions.add_function(".sort", (tuple, ))
def _sort(l):
    """
 _sort
 Ordena una tupla/lista
-----
*Parámetros:
l Tupla/Lista a ser ordenada
  
*Regresa: Lista ordenada
-----
    """
    return tuple(sorted(l))


@actions.add(".substring", 3)
@agentspeak.optimizer.function_like
def _substring(agent, term, intention):
    """
    _substring
 Verifica si un término es una subcadena de otro
-----
*Parámetros:
agent Agente activo
term  Términos a ser comparados
intention Pila de intenciones del agente
 
*Regresa: Nada
-----
    """
    needle = asl_str(agentspeak.grounded(term.args[0], intention.scope))
    haystack = asl_str(agentspeak.grounded(term.args[1], intention.scope))

    choicepoint = object()

    pos = haystack.find(needle)
    while pos != -1:
        intention.stack.append(choicepoint)

        if agentspeak.unify(term.args[2], pos, intention.scope, intention.stack):
            yield

        agentspeak.reroll(intention.scope, intention.stack, choicepoint)
        pos = haystack.find(needle, pos + 1)


@actions.add(".member", 2)
@agentspeak.optimizer.function_like
def _member(agent, term, intention):
    """
    _member
 Determina si un término es miembro de una lista
-----
*Parámetros:
agent Agente activo
term  Términos a ser comparados
intention Pila de intenciones del agente

 *Regresa: Nada
-----
    """
    choicepoint = object()

    for member in agentspeak.evaluate(term.args[1], intention.scope):
        intention.stack.append(choicepoint)

        if agentspeak.unify(term.args[0], member, intention.scope, intention.stack):
            yield

        agentspeak.reroll(intention.scope, intention.stack, choicepoint)


actions.add_predicate(".atom", (None, ), agentspeak.is_atom)
actions.add_predicate(".literal", (None, ), agentspeak.is_literal)
actions.add_predicate(".list", (None, ), agentspeak.is_list)
actions.add_predicate(".number", (None, ), agentspeak.is_number)
actions.add_predicate(".string", (None, ), agentspeak.is_string)
actions.add_predicate(".structure", (None, ), agentspeak.is_structure)


@actions.add(".ground", 1)
@agentspeak.optimizer.no_scope_effects
def _ground(agent, term, intention):
    """
    _ground
 Determina si un término está instanciado (tiene valor)
-----
*Parámetros:
agent Agente activo
term  Término a ser evaluado
intention Pila de intenciones del agente
 
*Regresa: 
-----
    """
    if agentspeak.is_ground(term, intention.scope):
        yield


@actions.add(".findall", 3)
@agentspeak.optimizer.function_like
def _findall(agent, term, intention):
    """
    _findall
 Devuelve los términos que unifican con el parámetro recibido en la pila de intenciones
-----
*Parámetros:
agent Agente activo
term  Término a buscar
intention Pila de intenciones del agente
 
*Regresa: Nada
-----
    """
    pattern = agentspeak.evaluate(term.args[0], intention.scope)
    query = agentspeak.runtime.TermQuery(term.args[1])
    result = []

    memo = {}
    for _ in query.execute(agent, intention):
        result.append(agentspeak.freeze(pattern, intention.scope, memo))

    if agentspeak.unify(tuple(result), term.args[2], intention.scope, intention.stack):
        yield


@actions.add(".count", 2)
@agentspeak.optimizer.function_like
def _count(agent, term, intention):
    """
    _count
 Devluelve el número de términos que unifican con el parámetro dado
-----
*Parámetros:
agent Agente activo
term  Término a buscar
intention Pila de intenciones del agente
   
*Regresa: Nada
-----
    """
    query = agentspeak.runtime.TermQuery(term.args[0])

    choicepoint = object()
    count = 0
    intention.stack.append(choicepoint)
    for _ in query.execute(agent, intention):
        count += 1
    agentspeak.reroll(intention.scope, intention.stack, choicepoint)

    if agentspeak.unify(count, term.args[1], intention.scope, intention.stack):
        yield


@actions.add(".abolish", 1)
# TODO: Inform optimizer.
def _abolish(agent, term, intention):
    """
    _abolish
 Elimina creencias de la base de la gente
-----
*Parámetros:
agent Agente activo
term  Término que representa la creencia
intention Pila de intenciones del agente
 
*Regresa: Nada
-----
    """
    memo = {}
    pattern = agentspeak.freeze(term.args[0], intention.scope, memo)
    group = agent.beliefs[pattern.literal_group()]

    for old_belief in list(group):
        if agentspeak.unifies_annotated(old_belief, pattern):
            group.remove(old_belief)

    yield


@actions.add(".date", 3)
@agentspeak.optimizer.side_effect(
    agentspeak.optimizer.InferenceEvilnessConst.AFFECT_PARAM_ALL,
    agentspeak.optimizer.InferenceEvilnessConst.EFFECT_DOBIND
)
def _date(agent, term, intention):
"""
_date
 Devuelve una fecha
-----
*Parámetros:
agent Agente activo
term  Término que unificará con la fecha devuelta
intention Pila de intenciones del agente 

*Regresa: Nada
-----
"""
    date = datetime.datetime.now()

    if (agentspeak.unify(term.args[0], date.year, intention.scope, intention.stack) and
        agentspeak.unify(term.args[1], date.month, intention.scope, intention.stack) and
        agentspeak.unify(term.args[2], date.day, intention.scope, intention.stack)):

        yield


@actions.add(".time", 3)
@agentspeak.optimizer.side_effect(
    agentspeak.optimizer.InferenceEvilnessConst.AFFECT_PARAM_ALL,
    agentspeak.optimizer.InferenceEvilnessConst.EFFECT_DOBIND
)
def _time(agent, term, intention):
    """
 _time
 Devuelve una marca temporal
-----
*Parámetros:
agent Agente activo
term  Término que unificará con la marca de tiempo
intention Pila de intenciones del agente
 
*Regresa: Nada
-----
    """
    time = datetime.datetime.now()

    if (agentspeak.unify(term.args[0], time.hour, intention.scope, intention.stack) and
        agentspeak.unify(term.args[1], time.minute, intention.scope, intention.stack) and
        agentspeak.unify(term.args[2], time.second, intention.scope, intention.stack)):

        yield


@actions.add(".wait", 1)
@actions.add(".wait", 2)
@agentspeak.optimizer.all_bound
def _wait(agent, term, intention):
    """
 _wait
 Retrasa el paso de razonamiento en n cantidad de milisegundos
-----
*Parámetros:
agent Agente activo
term  Término que unifica con el evento a ser retardado
intention Pila de intenciones del agente
 
*Regresa: Nada
-----
    """
    # Handle optional arguments.
    args = [agentspeak.grounded(arg, intention.scope) for arg in term.args]
    if len(args) == 2:
        event, millis = args
    else:
        if agentspeak.is_number(args[0]):
            millis = args[0]
            event = None
        else:
            millis = None
            event = args[0]

    # Type checks.
    if not (millis is None or agentspeak.is_number(millis)):
        raise agentspeak.AslError("expected timeout for .wait to be numeric")
    if not (event is None or agentspeak.is_string(event)):
        raise agentspeak.AslError("expected event for .wait to be a string")

    # Event.
    if event is not None:
        # Parse event.
        if not event.endswith("."):
            event += "."
        log = agentspeak.Log(LOGGER, 1)
        tokens = agentspeak.lexer.TokenStream(agentspeak.StringSource("<.wait>", event), log)
        tok, ast_event = agentspeak.parser.parse_event(tokens.next(), tokens, log)
        if tok.lexeme != ".":
            raise log.error("expected no further tokens after event for .wait, got: '%s'", tok.lexeme, loc=tok.loc)

        # Build term.
        event = ast_event.accept(agentspeak.runtime.BuildEventVisitor(log))

    # Timeout.
    if millis is None:
        until = None
    else:
        until = agent.env.time() + millis / 1000

    # Create waiter.
    intention.waiter = agentspeak.runtime.Waiter(event=event, until=until)
    yield


# Custom actions for debugging:


@actions.add(".range", 2)
@agentspeak.optimizer.function_like
def _range_2(agent, term, intention):
    
    choicepoint = object()

    for i in range(int(agentspeak.grounded(term.args[0], intention.scope))):
        intention.stack.append(choicepoint)

        if agentspeak.unify(term.args[1], i, intention.scope, intention.stack):
            yield

        agentspeak.reroll(intention.scope, intention.stack, choicepoint)


@actions.add(".dump", 0)
@agentspeak.optimizer.no_scope_effects
def _dump(agent, term, intention):
    agent.dump()
    yield


@actions.add(".unbind_all", 0)
@agentspeak.optimizer.side_effect(
    agentspeak.optimizer.InferenceEvilnessConst.AFFECT_SCOPE,
    agentspeak.optimizer.InferenceEvilnessConst.EFFECT_UNBIND
)
def _unbind_all(agent, term, intention):
    """
 _unbind_all
 Libera los términos instanciados del agente
-----
*Parámetros:
agent Agente activo
term  No usado
intention Pila de intenciones del agente
 
*Regresa: Nada
-----
"""
    intention.scope.clear()
    yield


@actions.add(".control_flow", 0)
@agentspeak.optimizer.no_scope_effects
def _control_flow(agent, term, intention):
    """
 _control_flow
 Crea una gráfica con los planes del agente a manera de representación del flujo de control
-----
*Parámetros:
agent Agente activo
term  No usado
intention Pila de intenciones del agente
 
*Regresa: Nada
-----
    """
    out = open("control_flow.dot", "w")
    print("digraph control_flow {", file=out)
    for plans in agent.plans.values():
        for plan in plans:
            print("  \"%s %s\" -> \"%s\";" % (plan.name(), plan.context, plan.body), file=out)
            closed_instrs = set()
            open_instrs = set([plan.body])
            while open_instrs:
                instr = open_instrs.pop()

                if instr.success:
                    print("  \"%s\" -> \"%s\";" % (instr, instr.success), file=out)

                if instr.failure:
                    print("  \"%s\" -> \"%s\" [label=\"failure\"];" % (instr, instr.failure), file=out)

                closed_instrs.add(instr)
                if instr.success and instr.success not in closed_instrs:
                    open_instrs.add(instr.success)
                if instr.failure and instr.failure not in closed_instrs:
                    open_instrs.add(instr.failure)
    print("}", file=out)
    out.close()
    print("Graph dumped to control_flow.dot")
    yield


# Add the actions used by the optimizer as markers
agentspeak.optimizer.init_optimizer_actions(actions)
