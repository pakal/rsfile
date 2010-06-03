#!/usr/bin/env python
# -*- coding: utf-8 -*-

'''
Created on 21 déc. 2009

@author: Admin
'''

# PAKAL - implementer la fonction SYNC dans rsFile ?? non, existe pas sous win32
# mais http://stackoverflow.com/questions/85595/flush-disk-cache-from-windows-cli
# et ca demande trop de privileges !!


import sys, os, functools
from contextlib import contextmanager


class TransactionFailure(Exception):
    pass

class TransactionRecordingFailure(TransactionFailure):
    pass

class TransactionRollbackFailure(TransactionFailure):
    pass


'''
@staticmethod
def _pack_arguments(*args, **kwargs):
    """
    This static method simply returns its arguments as
    a standard tuple (args, kwargs), with args being a list of positional 
    arguments, and kwargs a dict of keyword arguments.
    This might be of some use to easily pack the values to be returned 
    by meth`preprocess_arguments`.
    """
    return (args, kwargs)
'''




class TransactionalActionBase(object):
    """
    This abstract class defines the interface and semantic of "transactional action" objects.
    """
    
    

    
    def preprocess_arguments(self, *args, **kwargs):
        """
        Method called just before executing the action.
        Its only role is to transform the arguments received by the action, 
        into a set of context-independent parameters (maybe with the help of instance-specific
        attributes), which fully determine what the action will do.
        For example, such a treatment might transform relative path into absolute ones, 
        and determine the resources needed to perform the action in an "undo-able" way.
        The tuple (args, kwargs) that this method returns will be recorded, and expanded 
        in input (i.e *args and **kwargs)to :meth:`process_action` and m:eth:`rollback_action`.
        """
        return (args, kwargs)
    
    @staticmethod
    def process_action(*args, **kwargs):
        """
        This static method receives preprocessed arguments in input, and
        shall perform the transactional action it represents, returning its result (if any).
        Any error preventing the success of this action shall simply be left propagating, so 
        that upper level transactional structures can take measures accordingly (:meth:`rollback_action` 
        shall not be directly called by this method).
        Note that the signature and return type of this method are free, as long as expected arguments 
        match the output of the potential :meth:`preprocess_arguments` method.
        """
        raise NotImplementedError()
    
    @staticmethod
    def rollback_action(args, kwargs, was_interrupted, result=None):
        """
        This static method shall determine and undo all the changes made by a previous
        :meth:`process_action` call.
        If :meth:`process_action` was interrupted by a crash or an exception, *was_interrupted*
        is True, and *result* is None. Else, result is the value (if any) which was returned by the 
        meth:`process_action` call - this might be an appreciable hint in some circumstances.
        In any case, args and kwargs are the list and dict which contain the arguments whith which 
        :meth:`process_action` was called.
        In case of trouble preventing the rollback, this method shall raise an exception.
        No return value is expected.
        """
        raise NotImplementedError()
    

_function_interrupted = object()

class TransactionalActionAdapter(TransactionalActionBase):
    """
    This class provides a handy way of creating transactional action instances.
    Instead of subclassing :class:`TransactionalActionBase`, you may simply instanciate
    this class by providing process_action and rollback_action callables (with potentially a 
    preprocess_arguments one, which must NOT expect 'self' as first argument).
    The resulting object will behave like the instance of a subclass of :class:`TransactionalActionBase`,
    which would have overriden necessary methods.
    """
    
    
    
    def __init__(self, process_action, rollback_action, preprocess_arguments=None):
        
        assert process_action and rollback_action
        
        self._preprocess_arguments = preprocess_arguments
        self._process_action = process_action
        self._rollback_action = rollback_action
    
    def preprocess_arguments(self, *args, **kwargs):
        if not self._preprocess_arguments:
            return (args, kwargs) # default preprocessing : do nothing
        else:
            return self._preprocess_arguments(*args, **kwargs)
    
    def process_action(self, *args, **kwargs):
        return self._process_action(*args, **kwargs)
    
    def rollback_action(self, args, kwargs, was_interrupted, result=_function_interrupted):
        assert (was_interrupted and result is _function_interrupted) or (not was_interrupted and not result is _function_interrupted)
        return self._rollback_action(args, kwargs, was_interrupted, result)




class transactionalActionRegistry(object):
   
   
    def __init__(self, *source_action_registries, **initial_actions):
        
        # First, we check that no conflict will happen with the different names
        all_names = initial_actions.keys()
        for source in source_action_registries:
            all_names += source.list_registered_actions()
        assert len(all_names) == len(set(all_names)) # else, duplicate names found...
        for name in all_names:
            self._check_action_name(name)
   
        # Now, we mix sources together
        self._registered_actions = initial_actions  # couples name->TransactionalActionBase
        for source in source_action_registries:
            self._registered_actions.update(source.get_registry())
    
    def _check_action_name(self, name):
        assert not name.startswith("_") and not name.startswith("tx_") # we do not want conflicts with normal methods       
            
    def register_action(self, name, action):
        assert name not in self._registered_actions
        self._check_action_name(name)
        self._registered_actions[name] = action
    
    def unregister_action(self, name):
        assert name in self._registered_actions
        del self._registered_actions[name]
        
    def list_registered_actions(self):
        return self._registered_actions.keys()

    def get_action(self, name):
        assert name in self._registered_actions
        return self._registered_actions[name]

    def get_registry(self):
        return self._registered_actions






class ActionRecorderBase(object):
    
    _BEGIN_RECORD = 0
    _END_RECORD = 1
        
        
    def __init__(self, media_header=None):
        self._performed_actions_log = []
        self._savepoint_indexes = [] # sorted positions of different savepoints, as slice index values

        if media_header is not None:
            self._initialize_recorder_media(media_header)


    ### Methods to manage savepoints ###

    def create_savepoint(self):
        assert self.is_empty() or self.last_action_is_finished() # no savepoint inside an unfinished action !
        self._savepoint_indexes.append(len(self._performed_actions_log))
    
    def get_savepoint_count(self):
        return len(self._savepoint_indexes)
    
    def get_action_count_since_last_savepoint(self):
        assert self.get_savepoint_count()
        savepoint_position = self._savepoint_indexes[-1]
        records_concerned = len(self._performed_actions_log) - savepoint_position
        return (records_concerned / 2 + records_concerned % 2) # one of the actions might be unfinished...

    def commit_last_savepoint(self):
        assert self.is_empty() or self.last_action_is_finished() # no commit inside an unfinished action !
        assert self.get_savepoint_count()
        del self._savepoint_indexes[-1]
    
    def rollback_last_savepoint(self):
        assert self.get_savepoint_count()
        # we can only rollback the savepoint when following actions have been rolled back too
        assert self._savepoint_indexes[-1] == len(self._performed_actions_log) 
        del self._savepoint_indexes[-1]
            
    def _check_savepoints_integrity(self):
        if self.get_savepoint_count():
            assert self._savepoint_indexes[-1] <= len(self._performed_actions_log) # savepoints must not point beyond the action stack 



    ### Methods to retrieve information of recorded actions ###

    def is_empty(self):
        return not self._performed_actions_log
    
    def get_action_count(self):
        # Returns both finished actions, and a potential unfinished last action
        return len([i for i in self._performed_actions_log if i[0] == self._BEGIN_RECORD])
    
    def last_action_is_finished(self):
        assert not self.is_empty()
        # WARNING - TO BE MODIFIED WHEN ADDING SAVEPOINTS
        if self._performed_actions_log and self._performed_actions_log[-1][0] == self._END_RECORD:
            return True
        return False # This means that the last action is in UNFINISHED state



    ### Methods to process new actions ###
                 
    def begin_action_processing(self, value):
        assert not self._performed_actions_log or self._performed_actions_log[-1][0] == self._END_RECORD
        record = (self._BEGIN_RECORD, value)
        self._performed_actions_log.append(record)
        self._append_record_to_media(self._BEGIN_RECORD, value)
        
    def finish_action_processing(self, value):   
        assert self._performed_actions_log and self._performed_actions_log[-1][0] == self._BEGIN_RECORD  
        record = (self._END_RECORD, value)
        self._performed_actions_log.append(record)        
        self._append_record_to_media(self._END_RECORD, value)



    ### Methods to rollback a single action ###

    def get_unfinished_action(self):
        assert not self.last_action_is_finished() # also fails if recorder is empty
        return self._performed_actions_log[-1][1]
        
    def rollback_unfinished_action(self):
        assert not self.last_action_is_finished()
        self._performed_actions_log.pop() # removes last element
        self._remove_last_record_from_media()
        if __debug__: self._check_savepoints_integrity()
           
    def get_finished_action(self):
        assert self.last_action_is_finished()
        return (self._performed_actions_log[-2][1], self._performed_actions_log[-1][1])
        
    def rollback_finished_action(self):
        assert self.last_action_is_finished()
        for _ in range(2): # we pop the beginning and ending records
            self._performed_actions_log.pop() # removes last element
            self._remove_last_record_from_media()
            if __debug__: self._check_savepoints_integrity()



    ### Method to finalize the recording ###

    def commit_transaction(self):
        assert self.is_empty() or self.last_action_is_finished()
        assert not self.get_savepoint_count() # all savepoints must be rolled back or committed before !
        self._performed_actions_log = [] # full reinitialization, allowing further use of the transaction and recorder objects
        self._commit_transaction_to_media()
        

    ### Data persistence methods, to be overriden in subclasses ###
    def _initialize_recorder_media(self, value):
        pass
    
    def _append_record_to_media(self, record_type, value):
        pass # there, save to DB or to synchronized disk...
    
    def _remove_last_record_from_media(self):
        pass # there, save to DB or to synchronized disk... 

    def _commit_transaction_to_media(self):
        pass # there, save to DB or to synchronized disk... 





""" DEPRECATED
 __metaclass__ = TransactionMetaclass # creates a class attribute "_registered_actions"
 
class TransactionMetaclass(type):
    "
    This metaclass ensures that all transaction classes have dedicated
    _registered_actions dict, a specific set of transactional actions, so that 
    action registration in a transaction class doesn't interfer with others
    "
    
    def __init__(cls, name, bases, dict):
        object.__init__(name, bases, dict)
        if not "_registered_actions" in cls.__dict__:
            cls._registered_actions = {}
            
"""



class TransactionBase(object):

    
    def __init__(self, action_registry, action_recorder = None):
        
        self._action_registry = action_registry
        
        if not action_recorder:
            action_recorder = ActionRecorderBase()
        self._action_recorder = action_recorder
        
        
    def __getattr__(self, name):
        if not name in self._action_registry.list_registered_actions():
            raise AttributeError("Action Registry of %r has no action called %s" % (self, name))
        return functools.partial(self.tx_process_action, name)
    
    
    
    def _execute_selected_action(self, name, args=[], kwargs={}):
        

        action = self._action_registry.get_action(name) # might raise exceptions - no rollback needed in this case     
        (new_args, new_kwargs) = action.preprocess_arguments(*args, **kwargs) # might raise exceptions - no rollback needed in this case     
        
        try:
            self._begin_action_processing(name, new_args, new_kwargs)
        except Exception, e: 
            raise TransactionRecordingFailure(repr(e)), None, sys.exc_info()[2]   
                
        result = action.process_action(*new_args, **new_kwargs) # might raise exceptions - recovery needed then

        try:
            self._finish_action_processing(result)
        except Exception, e: 
            raise TransactionRecordingFailure(repr(e)), None, sys.exc_info()[2]    
    
        return result
    
    
    def _rollback_to_last_consistent_state(self):
        """
        
        May raise TransactionRecordingFailure errors, or any exception raised by the rollback operation.
        """
        
        try:
            need_unfinished_action_rollback = not self._action_recorder.is_empty() and not self._action_recorder.last_action_is_finished()
        except Exception, e: 
            raise TransactionRecordingFailure(repr(e)), None, sys.exc_info()[2]
                    
        if need_unfinished_action_rollback:
            
            try:
                (name, args, kwargs) = self._action_recorder.get_unfinished_action()
                action = self._action_registry.get_action(name)
            except Exception, e: 
                raise TransactionRecordingFailure(repr(e)), None, sys.exc_info()[2]    
            
            action.rollback_action(args=args, kwargs=kwargs, was_interrupted=True) # we try to rollback the unfinished action
    
            try:
                self._action_recorder.rollback_unfinished_action()
            except Exception, e: 
                raise TransactionRecordingFailure(repr(e)), None, sys.exc_info()[2]   
            
            return True
               
        return False


    def _rollback_consistent_transaction(self, rollback_to_last_savepoint=False):
        """
        Warning : if rollback_to_last_savepoint is True, the last savepoint itself is NOT removed !
        """
        assert self._action_recorder.is_empty() or self._action_recorder.last_action_is_finished()
        
        if rollback_to_last_savepoint:
            actions_to_undo = self._action_recorder.get_action_count_since_last_savepoint()
        else:
            assert not self._action_recorder.get_savepoint_count()
            actions_to_undo = self._action_recorder.get_action_count()
            
            
        for _ in range(actions_to_undo):
            
            try:
                ((name, args, kwargs), result) = self._action_recorder.get_finished_action()
                action = self._action_registry.get_action(name)
            except Exception, e: 
                raise TransactionRecordingFailure(repr(e)), None, sys.exc_info()[2]    
            
            action.rollback_action(args=args, kwargs=kwargs, was_interrupted=False, result=result) # we try to rollback the last finished action
    
            try:
                self._action_recorder.rollback_finished_action()
            except Exception, e: 
                raise TransactionRecordingFailure(repr(e)), None, sys.exc_info()[2]               
            
            assert rollback_to_last_savepoint or self._action_recorder.is_empty()
            
    
    def _commit_consistent_transaction(self):
        
        assert self._action_recorder.is_empty() or self._action_recorder.last_action_is_finished()
    
        try:
            self._action_recorder.commit_transaction()
        except Exception, e: 
            raise TransactionRecordingFailure(repr(e)), None, sys.exc_info()[2]               
        
    
    
    def _begin_action_processing(self, name, args, kwargs):
        record = (name, args, kwargs)
        self._action_recorder.begin_action_processing(record)
        
    def _finish_action_processing(self, result):   
        self._action_recorder.finish_action_processing(result)
    
    
    
    # To be overridden in subclasses !!!
    
    def tx_process_action(self, name, *args, **kwargs):
        raise NotImplementedError(__name__)
    
    def tx_rollback(self):
        raise NotImplementedError(__name__)
        
    def tx_commit(self):
        raise NotImplementedError(__name__)
    
    
    def tx_create_savepoint(self):
        raise NotImplementedError(__name__)
    
    def tx_rollback_savepoint(self):
        raise NotImplementedError(__name__)
    
    def tx_commit_savepoint(self):
        raise NotImplementedError(__name__)





class InteractiveTransaction(TransactionBase):

    
    
    def tx_process_action(self, name, *args, **kwargs):
        
        assert self._action_recorder.is_empty() or self._action_recorder.last_action_is_finished() # no unfinished action must be pending
        
        try:
            return self._execute_selected_action(name, args, kwargs)
        except TransactionFailure:
            raise # that's very bad... just let it propagate
        except Exception, e:
            try:
                self._rollback_to_last_consistent_state()
                raise # we reraise the original exception
            except Exception, f:
                #TODO - PY3K - real exception chaining required here !
                raise TransactionRollbackFailure, ("%r raised during rollback attempt, after receiving %r" % (f,e)), sys.exc_info()[2] 
                
    def tx_rollback(self):
        try:
            self._rollback_to_last_consistent_state() # in case the last action processing gave a TransactionRollbackFailure
            self._rollback_consistent_transaction()  
        except Exception, f:
            #TODO - PY3K - real exception chaining required here !
            raise TransactionRollbackFailure, ("%r raised during rollback attempt" % f), sys.exc_info()[2] 
                
    def tx_commit(self):
        self._commit_consistent_transaction()
    
    
    @contextmanager
    def tx_savepoint(self):
        self.tx_create_savepoint()
        try:
            yield 
        except TransactionFailure:
            raise # we must not try to handle this critical problem by ourselves...
        except Exception:
            self.tx_rollback_savepoint()
            raise
        else:
            self.tx_commit_savepoint()
    
    def tx_create_savepoint(self):
        self._action_recorder.create_savepoint()
    
    def tx_rollback_savepoint(self):
        self._rollback_consistent_transaction(rollback_to_last_savepoint=True)
        self._action_recorder.rollback_last_savepoint()
        
    def tx_commit_savepoint(self):
        self._action_recorder.commit_last_savepoint()
    

    
    
    
    
    